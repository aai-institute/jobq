from jobs.job import ResourceOptions


def test_resource_options_docker():
    opts = ResourceOptions(memory="1024Mi", cpu="200m")
    actual = opts.to_docker()

    assert actual["mem_limit"] == str(1024 * 2**20)
    assert actual["nano_cpus"] == int(0.2 * 10**9)


def test_resource_options_k8s():
    opts = ResourceOptions(memory="1024Mi", cpu="200m")
    actual = opts.to_kubernetes()

    assert actual["memory"] == opts.memory
    assert actual["cpu"] == opts.cpu
