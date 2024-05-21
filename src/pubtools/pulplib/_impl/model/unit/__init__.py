from .base import Unit, type_ids_for_class
from .file import FileUnit
from .rpm import RpmUnit, RpmDependency
from .erratum import (
    ErratumUnit,
    ErratumReference,
    ErratumPackageCollection,
    ErratumPackage,
    ErratumModule,
)
from .repo_metadata import YumRepoMetadataFileUnit
from .modulemd import ModulemdUnit, ModulemdDependency
from .modulemd_defaults import ModulemdDefaultsUnit

SUPPORTED_UNIT_TYPES = ("iso", "rpm", "srpm", "modulemd", "modulemd_defaults")
