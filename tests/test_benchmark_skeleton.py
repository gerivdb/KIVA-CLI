from pytest_benchmark.fixture import BenchmarkFixture


def test_latency(benchmark: BenchmarkFixture) -> None:
    def run() -> int:
        x = 0
        for i in range(1000):
            x += i
        return x

    benchmark(run)


def test_throughput(benchmark: BenchmarkFixture) -> None:
    def run() -> int:
        v = [i for i in range(1000)]
        return len(v)

    benchmark(run)
