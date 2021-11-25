from os.path import join, dirname
import pkg_resources


def resource_filename(path: str) -> str:
    # if __name__ == '__main__':
    #     return join(dirname(__file__), path)
    # else:
    return pkg_resources.resource_filename(__name__, path)


def resource_stream(path: str):
    # if __name__ == '__main__':
    #     return open(join(dirname(__file__), path))
    # else:
    return pkg_resources.resource_stream(__name__, path)


def resource_string(path: str) -> bytes:
    # if __name__ == '__main__':
    #     with open(join(dirname(__file__), path)) as f:
    #         return f.read().encode("utf8")
    # else:
    return pkg_resources.resource_string(__name__, path)
