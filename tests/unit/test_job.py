from jobs.job import ResourceOptions


def test_resource_options_docker():
    opts = ResourceOptions(memory="1024Mi", cpu="200m")
    actual = opts.to_docker()

    assert actual["mem_limit"] == str(1024 * 2**20)
    assert actual["nano_cpus"] == int(0.2 * 10**9)
