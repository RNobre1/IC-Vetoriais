"""Amostrador contínuo de recursos do host e de contêineres cgroup v2.

Grava a 1 Hz (ou intervalo configurado) um arquivo CSV com telemetria leve do
host (/proc e /sys) e de cada contêiner dos SGBDs sob teste. Usado durante toda a
sessão de medição de benchmarks para atribuir uso de CPU, memória residente,
swap e pressão (PSI) a cada fase.

Decisões de projeto:
- Custo baixo no laço: lê diretamente os pseudo-arquivos de /proc e cgroup v2
  (/sys/fs/cgroup/system.slice/docker-<ID>.scope/), sem invocar `docker stats`
  ou comandos pesados a cada segundo.
- Re-resolução dinâmica de IDs: quando contêineres são recriados (ex.:
  `docker compose down -v && up`), o inspect do Docker só é chamado sob demanda
  para atualizar o hash do cgroup se a leitura falhar.
- Resiliência a ausência temporária: contêineres desligados ou reiniciando geram
  células vazias sem derrubar o monitor.
- Conclusão limpa: captura SIGINT e SIGTERM, finalizando a escrita com flush e
  saindo com status 0.
"""

from __future__ import annotations

import argparse
import contextlib
import glob
import signal
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

Executor = Callable[[Sequence[str]], str]
LeitorArquivo = Callable[[str], str | None]
LeitorGlob = Callable[[str], list[str]]

COLUNAS_HOST_BASE = [
    "ts_utc",
    "t_mono_s",
    "mem_total_kb",
    "mem_available_kb",
    "swap_usado_kb",
    "pswpin",
    "pswpout",
    "cpu_host_ocupado",
    "cpu_host_total",
    "cpu_mhz_medio",
    "psi_mem_some_avg10",
    "psi_mem_full_avg10",
    "psi_cpu_some_avg10",
    "psi_io_some_avg10",
    "psi_io_full_avg10",
    "pgmajfault",
    "allocstall",
    "throttle_total",
]

SUFIXOS_CONTAINER = [
    "mem_current_b",
    "anon_b",
    "file_b",
    "inactive_file_b",
    "cpu_usec",
    "swap_current_b",
]


# ---------------------------------------------------------------------------
# Colaboradores padrão para I/O no sistema real
# ---------------------------------------------------------------------------


def leitor_sistema_real(caminho: str) -> str | None:
    """Lê arquivo do sistema operacional devolvendo string ou None se inacessível."""
    try:
        return Path(caminho).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def executor_docker_padrao(argv: Sequence[str]) -> str:
    """Executa comando Docker do sistema retornando stdout ou levantando erro."""
    proc = subprocess.run(list(argv), capture_output=True, text=True, timeout=15)
    if proc.returncode != 0:
        raise RuntimeError(f"Comando falhou ({' '.join(argv)}): {proc.stderr.strip()}")
    return proc.stdout


# ---------------------------------------------------------------------------
# Parsers puros (/proc, /sys e cgroup v2)
# ---------------------------------------------------------------------------


def ler_meminfo(texto: str) -> dict[str, int]:
    """Extrai total, disponível e swap de /proc/meminfo em kilobytes."""
    chaves = {
        "MemTotal:": "mem_total_kb",
        "MemAvailable:": "mem_available_kb",
        "SwapTotal:": "swap_total_kb",
        "SwapFree:": "swap_free_kb",
    }
    resultado: dict[str, int] = {}
    for linha in texto.splitlines():
        partes = linha.split()
        if len(partes) >= 2 and partes[0] in chaves:
            nome_campo = chaves[partes[0]]
            with contextlib.suppress(ValueError):
                resultado[nome_campo] = int(partes[1])
    return resultado


def ler_vmstat(texto: str) -> dict[str, int]:
    """Extrai pswpin, pswpout, pgmajfault e a soma de allocstall de /proc/vmstat."""
    resultado = {
        "pswpin": 0,
        "pswpout": 0,
        "pgmajfault": 0,
        "allocstall": 0,
    }
    tem_dado = False
    for linha in texto.splitlines():
        partes = linha.split()
        if len(partes) == 2:
            chave, val_str = partes[0], partes[1]
            try:
                val = int(val_str)
            except ValueError:
                continue

            tem_dado = True
            if chave in ("pswpin", "pswpout", "pgmajfault"):
                resultado[chave] = val
            elif chave.startswith("allocstall"):
                resultado["allocstall"] += val

    return resultado if tem_dado else {}


def ler_cpu_host(texto: str) -> tuple[int, int]:
    """Retorna (jiffies_ocupados, jiffies_totais) da linha agregada 'cpu ' de /proc/stat."""
    for linha in texto.splitlines():
        if linha.startswith("cpu "):
            partes = linha.split()[1:]
            valores = [int(p) for p in partes if p.isdigit()]
            if len(valores) >= 4:
                total = sum(valores)
                idle = valores[3]
                iowait = valores[4] if len(valores) >= 5 else 0
                ocupado = total - (idle + iowait)
                return ocupado, total
    return 0, 0


def ler_cpu_mhz_medio(texto: str) -> float:
    """Calcula a média de frequência de todos os núcleos listados em /proc/cpuinfo."""
    soma = 0.0
    qtd = 0
    for linha in texto.splitlines():
        if "cpu MHz" in linha and ":" in linha:
            val_str = linha.split(":", 1)[1].strip()
            try:
                soma += float(val_str)
                qtd += 1
            except ValueError:
                pass
    return soma / qtd if qtd > 0 else 0.0


def ler_psi(texto: str) -> dict[str, float]:
    """Extrai métricas avg10 de arquivos em /proc/pressure/{memory,cpu,io}."""
    resultado: dict[str, float] = {}
    for linha in texto.splitlines():
        partes = linha.split()
        if not partes:
            continue
        tipo = partes[0]  # "some" ou "full"
        for param in partes[1:]:
            if param.startswith("avg10="):
                try:
                    val = float(param.split("=", 1)[1])
                    if tipo == "some":
                        resultado["some_avg10"] = val
                    elif tipo == "full":
                        resultado["full_avg10"] = val
                except ValueError:
                    pass
    return resultado


def ler_thermal_throttle(conteudos: Sequence[str]) -> int | None:
    """Soma as contagens de throttle térmico dos núcleos/pacotes se presentes."""
    if not conteudos:
        return None
    total = 0
    encontrou = False
    for c in conteudos:
        val = ler_inteiro_simples(c)
        if val is not None:
            total += val
            encontrou = True
    return total if encontrou else None


def ler_inteiro_simples(texto: str) -> int | None:
    """Converte texto de arquivo com número único em inteiro ou retorna None."""
    s = texto.strip()
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        return None


def ler_memory_stat(texto: str) -> dict[str, int]:
    """Extrai anon, file e inactive_file de memory.stat do cgroup v2."""
    resultado: dict[str, int] = {}
    chaves_interesse = {"anon", "file", "inactive_file"}
    for linha in texto.splitlines():
        partes = linha.split()
        if len(partes) >= 2 and partes[0] in chaves_interesse:
            with contextlib.suppress(ValueError):
                resultado[partes[0]] = int(partes[1])
    return resultado


def ler_cpu_stat(texto: str) -> int | None:
    """Extrai usage_usec de cpu.stat do cgroup v2."""
    for linha in texto.splitlines():
        partes = linha.split()
        if len(partes) >= 2 and partes[0] == "usage_usec":
            try:
                return int(partes[1])
            except ValueError:
                pass
    return None


# ---------------------------------------------------------------------------
# Estruturação do CSV
# ---------------------------------------------------------------------------


def cabecalho_csv(containers: Sequence[str]) -> list[str]:
    """Gera a lista ordenada de colunas do CSV para o host e os contêineres dados."""
    cols = list(COLUNAS_HOST_BASE)
    for c in containers:
        for suf in SUFIXOS_CONTAINER:
            cols.append(f"{c}_{suf}")
    return cols


def formatar_linha_csv(valores: Sequence[Any]) -> str:
    """Formata sequência de valores para uma linha CSV UTF-8 terminada em newline."""
    itens: list[str] = []
    for v in valores:
        if v is None:
            itens.append("")
        elif isinstance(v, float):
            itens.append(f"{v:.3f}".rstrip("0").rstrip(".") if v % 1 != 0 else f"{v:.1f}")
        else:
            itens.append(str(v))
    return ",".join(itens) + "\n"


# ---------------------------------------------------------------------------
# Amostrador com cache e re-resolução de contêineres
# ---------------------------------------------------------------------------


class AmostradorHost:
    """Gerencia leitura de métricas do host e resolução de cgroups de contêineres."""

    def __init__(
        self,
        containers: Sequence[str],
        *,
        executor: Executor = executor_docker_padrao,
        leitor: LeitorArquivo = leitor_sistema_real,
        leitor_glob: LeitorGlob = glob.glob,
    ) -> None:
        self.containers = list(containers)
        self.executor = executor
        self.leitor = leitor
        self.leitor_glob = leitor_glob
        self._ids: dict[str, str] = {}

    def resolver_id_container(self, nome: str) -> str | None:
        """Resolve o ID completo do contêiner via docker inspect."""
        try:
            saida = self.executor(["docker", "inspect", "-f", "{{.Id}}", nome])
            cid = saida.strip()
            if cid:
                self._ids[nome] = cid
                return cid
        except Exception:
            self._ids.pop(nome, None)
        return None

    def ler_metricas_container(self, nome: str) -> dict[str, int | None]:
        """Lê métricas do cgroup v2 do contêiner, re-resolvendo ID se necessário."""
        cid = self._ids.get(nome)
        if not cid:
            cid = self.resolver_id_container(nome)
            if not cid:
                return {suf: None for suf in SUFIXOS_CONTAINER}

        def ler_cgroup(id_atual: str) -> dict[str, int | None] | None:
            caminho_base = f"/sys/fs/cgroup/system.slice/docker-{id_atual}.scope"
            conteudo_mem = self.leitor(f"{caminho_base}/memory.current")
            if conteudo_mem is None:
                return None

            mem_current_b = ler_inteiro_simples(conteudo_mem)

            conteudo_stat = self.leitor(f"{caminho_base}/memory.stat")
            m_stat = ler_memory_stat(conteudo_stat) if conteudo_stat else {}

            conteudo_cpu = self.leitor(f"{caminho_base}/cpu.stat")
            cpu_usec = ler_cpu_stat(conteudo_cpu) if conteudo_cpu else None

            conteudo_swap = self.leitor(f"{caminho_base}/memory.swap.current")
            swap_b = ler_inteiro_simples(conteudo_swap) if conteudo_swap else None

            return {
                "mem_current_b": mem_current_b,
                "anon_b": m_stat.get("anon"),
                "file_b": m_stat.get("file"),
                "inactive_file_b": m_stat.get("inactive_file"),
                "cpu_usec": cpu_usec,
                "swap_current_b": swap_b,
            }

        dados = ler_cgroup(cid)
        if dados is None:
            # Contêiner pode ter sido recriado: invalida e tenta resolver de novo
            self._ids.pop(nome, None)
            novo_cid = self.resolver_id_container(nome)
            if novo_cid:
                dados = ler_cgroup(novo_cid)

        if dados is None:
            return {suf: None for suf in SUFIXOS_CONTAINER}
        return dados


def coletar_amostra(
    amostrador: AmostradorHost,
    *,
    ts_utc: str,
    t_mono_s: float,
) -> dict[str, Any]:
    """Coleta um registro instantâneo completo de telemetria do host e contêineres."""
    linha: dict[str, Any] = {
        "ts_utc": ts_utc,
        "t_mono_s": f"{t_mono_s:.3f}",
    }

    # /proc/meminfo
    txt_meminfo = amostrador.leitor("/proc/meminfo")
    if txt_meminfo:
        info = ler_meminfo(txt_meminfo)
        linha["mem_total_kb"] = info.get("mem_total_kb")
        linha["mem_available_kb"] = info.get("mem_available_kb")
        s_total = info.get("swap_total_kb")
        s_free = info.get("swap_free_kb")
        if s_total is not None and s_free is not None:
            linha["swap_usado_kb"] = s_total - s_free
        else:
            linha["swap_usado_kb"] = None
    else:
        linha["mem_total_kb"] = None
        linha["mem_available_kb"] = None
        linha["swap_usado_kb"] = None

    # /proc/vmstat
    txt_vmstat = amostrador.leitor("/proc/vmstat")
    if txt_vmstat:
        vm = ler_vmstat(txt_vmstat)
        linha["pswpin"] = vm.get("pswpin")
        linha["pswpout"] = vm.get("pswpout")
        linha["pgmajfault"] = vm.get("pgmajfault")
        linha["allocstall"] = vm.get("allocstall")
    else:
        linha["pswpin"] = None
        linha["pswpout"] = None
        linha["pgmajfault"] = None
        linha["allocstall"] = None

    # /proc/stat
    txt_stat = amostrador.leitor("/proc/stat")
    if txt_stat:
        ocupado, total = ler_cpu_host(txt_stat)
        linha["cpu_host_ocupado"] = ocupado
        linha["cpu_host_total"] = total
    else:
        linha["cpu_host_ocupado"] = None
        linha["cpu_host_total"] = None

    # /proc/cpuinfo
    txt_cpuinfo = amostrador.leitor("/proc/cpuinfo")
    linha["cpu_mhz_medio"] = round(ler_cpu_mhz_medio(txt_cpuinfo), 2) if txt_cpuinfo else None

    # PSI
    txt_psi_mem = amostrador.leitor("/proc/pressure/memory")
    psi_mem = ler_psi(txt_psi_mem) if txt_psi_mem else {}
    linha["psi_mem_some_avg10"] = psi_mem.get("some_avg10")
    linha["psi_mem_full_avg10"] = psi_mem.get("full_avg10")

    txt_psi_cpu = amostrador.leitor("/proc/pressure/cpu")
    psi_cpu = ler_psi(txt_psi_cpu) if txt_psi_cpu else {}
    linha["psi_cpu_some_avg10"] = psi_cpu.get("some_avg10")

    txt_psi_io = amostrador.leitor("/proc/pressure/io")
    psi_io = ler_psi(txt_psi_io) if txt_psi_io else {}
    linha["psi_io_some_avg10"] = psi_io.get("some_avg10")
    linha["psi_io_full_avg10"] = psi_io.get("full_avg10")

    # Throttle térmico
    padroes_thermal = [
        "/sys/devices/system/cpu/cpu*/thermal_throttle/core_throttle_count",
        "/sys/devices/system/cpu/cpu*/thermal_throttle/package_throttle_count",
    ]
    arquivos_thermal: list[str] = []
    for p in padroes_thermal:
        arquivos_thermal.extend(amostrador.leitor_glob(p))

    if arquivos_thermal:
        conteudos = [amostrador.leitor(c) for c in arquivos_thermal]
        conteudos_validos = [c for c in conteudos if c is not None]
        linha["throttle_total"] = ler_thermal_throttle(conteudos_validos)
    else:
        linha["throttle_total"] = None

    # Contêineres
    for c in amostrador.containers:
        m = amostrador.ler_metricas_container(c)
        for suf in SUFIXOS_CONTAINER:
            linha[f"{c}_{suf}"] = m.get(suf)

    return linha


# ---------------------------------------------------------------------------
# Laço de execução contínua
# ---------------------------------------------------------------------------


def executar_monitor(
    saida: Path,
    intervalo: float,
    containers: Sequence[str],
    *,
    executor: Executor = executor_docker_padrao,
    leitor: LeitorArquivo = leitor_sistema_real,
    leitor_glob: LeitorGlob = glob.glob,
    deve_parar: Callable[[], bool] | None = None,
    relogio_mono: Callable[[], float] = time.monotonic,
) -> None:
    """Executa amostragem periódica escrevendo no arquivo CSV até sinal de parada."""
    saida.parent.mkdir(parents=True, exist_ok=True)
    cols = cabecalho_csv(containers)
    amostrador = AmostradorHost(
        containers, executor=executor, leitor=leitor, leitor_glob=leitor_glob
    )

    with saida.open("w", encoding="utf-8") as f:
        f.write(",".join(cols) + "\n")
        f.flush()

        while not (deve_parar is not None and deve_parar()):
            t0 = relogio_mono()
            agora_utc = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
            amostra = coletar_amostra(amostrador, ts_utc=agora_utc, t_mono_s=t0)
            valores = [amostra.get(col) for col in cols]
            f.write(formatar_linha_csv(valores))
            f.flush()

            t_amostragem = relogio_mono() - t0
            tempo_espera = max(0.0, intervalo - t_amostragem)
            if tempo_espera > 0:
                time.sleep(tempo_espera)


# ---------------------------------------------------------------------------
# CLI e Sinalização
# ---------------------------------------------------------------------------


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    """Interpreta argumentos de linha de comando."""
    p = argparse.ArgumentParser(
        prog="monitor", description="Amostrador de recursos do host e contêineres."
    )
    p.add_argument(
        "--saida",
        type=Path,
        required=True,
        help="Caminho do CSV de destino.",
    )
    p.add_argument(
        "--intervalo",
        type=float,
        default=1.0,
        help="Intervalo de amostragem em segundos (default: 1.0).",
    )
    p.add_argument(
        "--containers",
        type=lambda s: [c.strip() for c in s.split(",") if c.strip()],
        default=["ic-pgvector", "ic-qdrant", "ic-weaviate"],
        help="Lista de contêineres separados por vírgula.",
    )
    return p.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Ponto de entrada do CLI com captura de SIGINT e SIGTERM."""
    args = parse_args(sys.argv[1:] if argv is None else argv)

    parar = False

    def handler_sinal(signum: int, frame: Any) -> None:
        del signum, frame
        nonlocal parar
        parar = True

    signal.signal(signal.SIGINT, handler_sinal)
    signal.signal(signal.SIGTERM, handler_sinal)

    executar_monitor(
        saida=args.saida,
        intervalo=args.intervalo,
        containers=args.containers,
        deve_parar=lambda: parar,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
