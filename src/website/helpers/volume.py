import ctypes
import ctypes.util
import threading
from typing import Optional, ClassVar

class VolumeCapacity:
    """
    Capacities of the volume that holds a path, as macOS reports them to applications (Finder, About This Mac),
    read with the resource keys of CFURL (CoreFoundation, CFURL.h). Every method returns None outside of macOS,
    or when the value is not available.

    Unlike statvfs(), these count purgeable space (caches, local snapshots, iCloud files that can be downloaded again),
    which macOS frees when a program needs the space, as available.
    """

    # CFNumberType kCFNumberSInt64Type (CFNumber.h)
    NUMBER_SINT64: ClassVar[int] = 4

    library: ClassVar[Optional[ctypes.CDLL]] = None
    loaded: ClassVar[bool] = False
    lock: ClassVar[threading.Lock] = threading.Lock()

    @classmethod
    def available_for_important_usage(cls, path: str) -> Optional[int]:
        """Bytes available for data the user asked to keep (what Finder shows as available)."""
        return cls.read(path, "kCFURLVolumeAvailableCapacityForImportantUsageKey")

    @classmethod
    def available_for_opportunistic_usage(cls, path: str) -> Optional[int]:
        """Bytes available for data that can be created again, such as caches."""
        return cls.read(path, "kCFURLVolumeAvailableCapacityForOpportunisticUsageKey")

    @classmethod
    def available(cls, path: str) -> Optional[int]:
        """Bytes not allocated at all, as statvfs() reports them."""
        return cls.read(path, "kCFURLVolumeAvailableCapacityKey")

    @classmethod
    def total(cls, path: str) -> Optional[int]:
        return cls.read(path, "kCFURLVolumeTotalCapacityKey")

    @classmethod
    def read(cls, path: str, key_name: str) -> Optional[int]:
        """Reads the number of the CFURL resource key named `key_name` (a constant exported by CoreFoundation) for `path`."""
        library = cls.load()
        if library is None:
            return None
        try:
            key = ctypes.c_void_p.in_dll(library, key_name)
        except ValueError:
            return None

        encoded = path.encode("utf-8")
        url = library.CFURLCreateFromFileSystemRepresentation(None, encoded, len(encoded), True)
        if not url:
            return None
        try:
            value = ctypes.c_void_p()
            if not library.CFURLCopyResourcePropertyForKey(url, key, ctypes.byref(value), None) or not value.value:
                return None
            try:
                if library.CFGetTypeID(value) != library.CFNumberGetTypeID():
                    return None
                number = ctypes.c_int64()
                if not library.CFNumberGetValue(value, cls.NUMBER_SINT64, ctypes.byref(number)):
                    return None
                return number.value
            finally:
                library.CFRelease(value)
        finally:
            library.CFRelease(url)

    @classmethod
    def load(cls) -> Optional[ctypes.CDLL]:
        with cls.lock:
            if cls.loaded:
                return cls.library
            cls.loaded = True

            name = ctypes.util.find_library("CoreFoundation")
            if name is None:
                return None
            try:
                library = ctypes.CDLL(name)
            except OSError:
                return None

            library.CFURLCreateFromFileSystemRepresentation.restype = ctypes.c_void_p
            library.CFURLCreateFromFileSystemRepresentation.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_long, ctypes.c_bool]
            library.CFURLCopyResourcePropertyForKey.restype = ctypes.c_bool
            library.CFURLCopyResourcePropertyForKey.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p]
            library.CFGetTypeID.restype = ctypes.c_ulong
            library.CFGetTypeID.argtypes = [ctypes.c_void_p]
            library.CFNumberGetTypeID.restype = ctypes.c_ulong
            library.CFNumberGetTypeID.argtypes = []
            library.CFNumberGetValue.restype = ctypes.c_bool
            library.CFNumberGetValue.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
            library.CFRelease.restype = None
            library.CFRelease.argtypes = [ctypes.c_void_p]

            cls.library = library
            return library
