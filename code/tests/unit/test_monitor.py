"""Testes unitários do amostrador de recursos `lib.monitor` (TDD).

Cobre parsers puros com fixtures reais do host Fedora, geração do CSV,
resolução e re-resolução de IDs de contêineres e laço de amostragem.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lib.monitor import (
    AmostradorHost,
    cabecalho_csv,
    coletar_amostra,
    executar_monitor,
    formatar_linha_csv,
    ler_cpu_host,
    ler_cpu_mhz_medio,
    ler_cpu_stat,
    ler_inteiro_simples,
    ler_meminfo,
    ler_memory_stat,
    ler_psi,
    ler_thermal_throttle,
    ler_vmstat,
    parse_args,
)

# ---------------------------------------------------------------------------
# Parsers puros
# ---------------------------------------------------------------------------


def test_ler_meminfo() -> None:
    texto = (
        "MemTotal:       16013960 kB\n"
        "MemFree:         1234567 kB\n"
        "MemAvailable:   12345678 kB\n"
        "Buffers:          100000 kB\n"
        "Cached:           500000 kB\n"
        "SwapTotal:       2097148 kB\n"
        "SwapFree:        1048574 kB\n"
    )
    dados = ler_meminfo(texto)
    assert dados["mem_total_kb"] == 16013960
    assert dados["mem_available_kb"] == 12345678
    assert dados["swap_total_kb"] == 2097148
    assert dados["swap_free_kb"] == 1048574


def test_ler_vmstat() -> None:
    texto = (
        "nr_free_pages 308641\n"
        "pswpin 59235\n"
        "pswpout 718047\n"
        "pgmajfault 1520\n"
        "allocstall_dma 0\n"
        "allocstall_dma32 0\n"
        "allocstall_normal 12\n"
        "allocstall_movable 3\n"
        "pgpgin 829102\n"
    )
    dados = ler_vmstat(texto)
    assert dados["pswpin"] == 59235
    assert dados["pswpout"] == 718047
    assert dados["pgmajfault"] == 1520
    assert dados["allocstall"] == 15  # 12 + 3


def test_ler_cpu_host() -> None:
    texto = (
        "cpu  381319 9538 128138 3377837 303760 15794 7657 0 0 0\n"
        "cpu0 95329 2384 32034 844459 75940 3948 1914 0 0 0\n"
    )
    ocupado, total = ler_cpu_host(texto)
    # total = 381319 + 9538 + 128138 + 3377837 + 303760 + 15794 + 7657 = 4224043
    # idle = 3377837, iowait = 303760 -> idle_total = 3681597
    # ocupado = total - idle_total = 542446
    assert total == 4224043
    assert ocupado == 542446


def test_ler_cpu_mhz_medio() -> None:
    texto = (
        "processor	: 0\n"
        "cpu MHz		: 3838.657\n"
        "processor	: 1\n"
        "cpu MHz		: 3840.123\n"
    )
    mhz = ler_cpu_mhz_medio(texto)
    assert mhz == pytest.approx((3838.657 + 3840.123) / 2.0)


def test_ler_cpu_mhz_medio_vazio() -> None:
    assert ler_cpu_mhz_medio("") == 0.0


def test_ler_psi() -> None:
    texto_mem = (
        "some avg10=1.23 avg60=0.50 avg300=0.10 total=12345\n"
        "full avg10=0.45 avg60=0.20 avg300=0.05 total=6789\n"
    )
    psi_mem = ler_psi(texto_mem)
    assert psi_mem["some_avg10"] == pytest.approx(1.23)
    assert psi_mem["full_avg10"] == pytest.approx(0.45)

    texto_cpu = "some avg10=0.78 avg60=0.30 avg300=0.08 total=9876\n"
    psi_cpu = ler_psi(texto_cpu)
    assert psi_cpu["some_avg10"] == pytest.approx(0.78)
    assert "full_avg10" not in psi_cpu


def test_ler_thermal_throttle() -> None:
    conteudos = ["0\n", "5\n", "3\n"]
    assert ler_thermal_throttle(conteudos) == 8
    assert ler_thermal_throttle([]) is None


def test_ler_inteiro_simples() -> None:
    assert ler_inteiro_simples("190189568\n") == 190189568
    assert ler_inteiro_simples(" 0 ") == 0
    assert ler_inteiro_simples("") is None


def test_ler_memory_stat() -> None:
    texto = (
        "anon 190189568\n"
        "file 46391296\n"
        "kernel_stack 49152\n"
        "inactive_file 17530880\n"
        "active_file 28860416\n"
    )
    stat = ler_memory_stat(texto)
    assert stat["anon"] == 190189568
    assert stat["file"] == 46391296
    assert stat["inactive_file"] == 17530880


def test_ler_cpu_stat() -> None:
    texto = "usage_usec 32126124\n" "user_usec 24136942\n" "system_usec 7989181\n"
    assert ler_cpu_stat(texto) == 32126124


# ---------------------------------------------------------------------------
# Estrutura do CSV
# ---------------------------------------------------------------------------


def test_cabecalho_csv() -> None:
    cab = cabecalho_csv(["ic-pgvector", "ic-qdrant"])
    esperado = [
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
        "ic-pgvector_mem_current_b",
        "ic-pgvector_anon_b",
        "ic-pgvector_file_b",
        "ic-pgvector_inactive_file_b",
        "ic-pgvector_cpu_usec",
        "ic-pgvector_swap_current_b",
        "ic-qdrant_mem_current_b",
        "ic-qdrant_anon_b",
        "ic-qdrant_file_b",
        "ic-qdrant_inactive_file_b",
        "ic-qdrant_cpu_usec",
        "ic-qdrant_swap_current_b",
    ]
    assert cab == esperado


def test_formatar_linha_csv() -> None:
    valores = ["2026-11-15T12:00:00.000Z", "123.456", 1000, 800, None, ""]
    linha = formatar_linha_csv(valores)
    assert linha == "2026-11-15T12:00:00.000Z,123.456,1000,800,,\n"


# ---------------------------------------------------------------------------
# Coleta e Laço com Injeção
# ---------------------------------------------------------------------------


def test_amostrador_coleta_e_re_resolve_container() -> None:
    """Valida que contêiner ausente gera células vazias e troca de ID é re-resolvida."""
    chamadas_inspect: list[str] = []
    ids_docker = {
        "ic-pgvector": ["id1_full", "id2_full"],
    }

    def executor_fake(cmd: list[str]) -> str:
        # cmd: ["docker", "inspect", "-f", "{{.Id}}", nome]
        nome = cmd[4]
        chamadas_inspect.append(nome)
        lista = ids_docker.get(nome, [])
        if lista:
            return lista.pop(0) + "\n"
        raise RuntimeError(f"container {nome} nao encontrado")

    arquivos_cgroup = {
        "/sys/fs/cgroup/system.slice/docker-id1_full.scope/memory.current": "50000\n",
        "/sys/fs/cgroup/system.slice/docker-id1_full.scope/memory.stat": "anon 20000\nfile 30000\ninactive_file 10000\n",
        "/sys/fs/cgroup/system.slice/docker-id1_full.scope/cpu.stat": "usage_usec 1000\n",
        "/sys/fs/cgroup/system.slice/docker-id1_full.scope/memory.swap.current": "0\n",
        # id2
        "/sys/fs/cgroup/system.slice/docker-id2_full.scope/memory.current": "60000\n",
        "/sys/fs/cgroup/system.slice/docker-id2_full.scope/memory.stat": "anon 25000\nfile 35000\ninactive_file 15000\n",
        "/sys/fs/cgroup/system.slice/docker-id2_full.scope/cpu.stat": "usage_usec 2000\n",
        "/sys/fs/cgroup/system.slice/docker-id2_full.scope/memory.swap.current": "1000\n",
    }

    arquivos_host = {
        "/proc/meminfo": "MemTotal: 16000 kB\nMemAvailable: 8000 kB\nSwapTotal: 2000 kB\nSwapFree: 1000 kB\n",
        "/proc/vmstat": "pswpin 10\npswpout 20\npgmajfault 5\nallocstall_normal 2\n",
        "/proc/stat": "cpu  100 0 100 800 0 0 0 0 0 0\n",
        "/proc/cpuinfo": "cpu MHz : 2000.000\n",
        "/proc/pressure/memory": "some avg10=0.10 avg60=0.0 avg300=0.0 total=0\nfull avg10=0.05 avg60=0.0 avg300=0.0 total=0\n",
        "/proc/pressure/cpu": "some avg10=0.20 avg60=0.0 avg300=0.0 total=0\n",
        "/proc/pressure/io": "some avg10=0.30 avg60=0.0 avg300=0.0 total=0\nfull avg10=0.15 avg60=0.0 avg300=0.0 total=0\n",
    }

    def leitor_fake(caminho: str) -> str | None:
        if caminho in arquivos_host:
            return arquivos_host[caminho]
        return arquivos_cgroup.get(caminho)

    amostrador = AmostradorHost(
        containers=["ic-pgvector"],
        executor=executor_fake,
        leitor=leitor_fake,
        leitor_glob=lambda padrao: [],
    )

    # Amostra 1: id1 ativo
    l1 = coletar_amostra(amostrador, ts_utc="2026-11-15T12:00:00.000Z", t_mono_s=10.0)
    assert l1["ic-pgvector_mem_current_b"] == 50000
    assert l1["ic-pgvector_anon_b"] == 20000
    assert l1["ic-pgvector_swap_current_b"] == 0
    assert l1["swap_usado_kb"] == 1000  # 2000 - 1000

    # Simulando que id1 caiu (sumiu do cgroup)
    arquivos_cgroup.clear()
    l2 = coletar_amostra(amostrador, ts_utc="2026-11-15T12:00:01.000Z", t_mono_s=11.0)
    # Contêiner ausente -> campos ficam None/vazios, não levanta exceção
    assert l2["ic-pgvector_mem_current_b"] is None
    assert l2["ic-pgvector_cpu_usec"] is None

    # Simulando que o container voltou com id2_full
    # No próximo ciclo ele re-resolve
    arquivos_cgroup.update(
        {
            "/sys/fs/cgroup/system.slice/docker-id2_full.scope/memory.current": "60000\n",
            "/sys/fs/cgroup/system.slice/docker-id2_full.scope/memory.stat": "anon 25000\nfile 35000\ninactive_file 15000\n",
            "/sys/fs/cgroup/system.slice/docker-id2_full.scope/cpu.stat": "usage_usec 2000\n",
            "/sys/fs/cgroup/system.slice/docker-id2_full.scope/memory.swap.current": "1000\n",
        }
    )
    l3 = coletar_amostra(amostrador, ts_utc="2026-11-15T12:00:02.000Z", t_mono_s=12.0)
    assert l3["ic-pgvector_mem_current_b"] == 60000
    assert l3["ic-pgvector_cpu_usec"] == 2000
    assert l3["ic-pgvector_swap_current_b"] == 1000


def test_executar_monitor_grava_csv_ate_parar(tmp_path: Path) -> None:
    saida = tmp_path / "monitor.csv"
    iteracoes = [0]

    def leitor_fake(caminho: str) -> str | None:
        if caminho == "/proc/meminfo":
            return "MemTotal: 100 kB\nMemAvailable: 50 kB\nSwapTotal: 0 kB\nSwapFree: 0 kB\n"
        return None

    def relogio_mono() -> float:
        return 100.0 + iteracoes[0]

    def condicao_parada() -> bool:
        iteracoes[0] += 1
        return iteracoes[0] > 2

    executar_monitor(
        saida=saida,
        intervalo=0.01,
        containers=["ic-pgvector"],
        executor=lambda cmd: "id1\n",
        leitor=leitor_fake,
        leitor_glob=lambda padrao: [],
        deve_parar=condicao_parada,
        relogio_mono=relogio_mono,
    )

    linhas = saida.read_text(encoding="utf-8").strip().splitlines()
    assert len(linhas) == 3  # cabeçalho + 2 amostras
    cab = linhas[0].split(",")
    assert cab[0] == "ts_utc"
    assert "mem_total_kb" in cab
    assert "ic-pgvector_mem_current_b" in cab


def test_parse_args_monitor() -> None:
    args = parse_args(["--saida", "teste.csv", "--intervalo", "0.5", "--containers", "c1,c2"])
    assert args.saida == Path("teste.csv")
    assert args.intervalo == 0.5
    assert args.containers == ["c1", "c2"]


def test_main_monitor_chama_executar_e_retorna_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    saida = tmp_path / "saida.csv"
    chamou = []

    def fake_executar(
        saida: Path, intervalo: float, containers: list[str], deve_parar=None
    ) -> None:
        chamou.append((saida, intervalo, containers))
        if deve_parar:
            deve_parar()

    from lib import monitor

    monkeypatch.setattr(monitor, "executar_monitor", fake_executar)

    ret = monitor.main(["--saida", str(saida), "--intervalo", "0.2", "--containers", "pg,qd"])
    assert ret == 0
    assert len(chamou) == 1
    assert chamou[0][0] == saida
    assert chamou[0][1] == 0.2
    assert chamou[0][2] == ["pg", "qd"]
