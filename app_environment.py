from enum import Enum


class AppEnvironment(str, Enum):
    local = "local"
    test = "test"
    staging = "staging"
    production = "production"

    def is_remote_env(self) -> bool:
        return self == AppEnvironment.production or self == AppEnvironment.staging

    def is_production_env(self) -> bool:
        return self == AppEnvironment.production

    def is_staging_env(self) -> bool:
        return self == AppEnvironment.staging

    def is_test_env(self) -> bool:
        return self == AppEnvironment.test

    def is_local_env(self) -> bool:
        return self == AppEnvironment.local
