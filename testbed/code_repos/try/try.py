from taint_models.test_models import __test_source, __test_sink

source = __test_source()
a = 42
b = int(source)

__test_sink(a)
__test_sink(b)
