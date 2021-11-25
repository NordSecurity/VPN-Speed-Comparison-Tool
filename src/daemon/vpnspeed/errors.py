class VPNSpeedError(Exception):
    """Base exception for this module"""


class VPNBadCredentials(VPNSpeedError):
    """Unable to login to VPN provader with given credentials"""


class APIError(VPNSpeedError):
    """Api was used incorrectly"""


class TestGroupError(VPNSpeedError):
    """Failure indicating problem for test group"""


class TestCaseError(VPNSpeedError):
    """Failure indicating problem for test case"""


class TestRunError(VPNSpeedError):
    """Failure indicating problem for test run"""


class TesterServersNotFound(TestGroupError):
    """No servers found"""


class ProviderNotSupported(TestCaseError):
    """This provider is not supported"""


class TechnologyNotSupported(TestCaseError):
    """Technology not supported by this provider"""


class ProtocolNotSupported(TestCaseError):
    """Protocol not supported by this technology"""


class TechnologyAuthFailed(TestRunError):
    """Bad credentials for VPN Technology"""


class ProviderServerNotFound(TestRunError):
    """Cant resolve server for a provider"""


class ProviderAPIQueryFailed(TestRunError):
    """Failed provider API query"""


class VPNConnectionFailed(TestRunError):
    """Failed to establish vpn connection"""
