import importlib.util
import sys


def execute() -> None:
    module_file = sys.argv[1]
    module_name = module_file.replace("/", ".").removesuffix(".py")

    func_name = sys.argv[2]

    spec = importlib.util.spec_from_file_location(module_name, module_file)
    module = importlib.util.module_from_spec(spec)

    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    func = getattr(module, func_name)

    # Go go go!
    func()
