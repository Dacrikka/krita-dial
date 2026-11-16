"""Minimal Windows HID access in pure ctypes (SetupAPI + hid.dll + overlapped ReadFile).

No Krita/Qt imports: usable from a plain Python script for testing.
Windows only: a macOS backend would be a separate module with the same interface.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass

_setupapi = ctypes.WinDLL("setupapi", use_last_error=True)
_hid = ctypes.WinDLL("hid", use_last_error=True)
_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

DIGCF_PRESENT = 0x02
DIGCF_DEVICEINTERFACE = 0x10
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 0x01
FILE_SHARE_WRITE = 0x02
OPEN_EXISTING = 3
FILE_FLAG_OVERLAPPED = 0x40000000
INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value
ERROR_IO_PENDING = 997
ERROR_INSUFFICIENT_BUFFER = 122
ERROR_NO_MORE_ITEMS = 259
WAIT_OBJECT_0 = 0
WAIT_TIMEOUT = 0x102
HIDP_STATUS_SUCCESS = 0x00110000


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    ]


class SP_DEVICE_INTERFACE_DATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("InterfaceClassGuid", GUID),
        ("Flags", wintypes.DWORD),
        ("Reserved", ctypes.c_size_t),
    ]


class HIDD_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ("Size", wintypes.ULONG),
        ("VendorID", wintypes.USHORT),
        ("ProductID", wintypes.USHORT),
        ("VersionNumber", wintypes.USHORT),
    ]


class HIDP_CAPS(ctypes.Structure):
    _fields_ = [
        ("Usage", wintypes.USHORT),
        ("UsagePage", wintypes.USHORT),
        ("InputReportByteLength", wintypes.USHORT),
        ("OutputReportByteLength", wintypes.USHORT),
        ("FeatureReportByteLength", wintypes.USHORT),
        ("Reserved", wintypes.USHORT * 17),
        ("NumberLinkCollectionNodes", wintypes.USHORT),
        ("NumberInputButtonCaps", wintypes.USHORT),
        ("NumberInputValueCaps", wintypes.USHORT),
        ("NumberInputDataIndices", wintypes.USHORT),
        ("NumberOutputButtonCaps", wintypes.USHORT),
        ("NumberOutputValueCaps", wintypes.USHORT),
        ("NumberOutputDataIndices", wintypes.USHORT),
        ("NumberFeatureButtonCaps", wintypes.USHORT),
        ("NumberFeatureValueCaps", wintypes.USHORT),
        ("NumberFeatureDataIndices", wintypes.USHORT),
    ]


class OVERLAPPED(ctypes.Structure):
    _fields_ = [
        ("Internal", ctypes.c_size_t),
        ("InternalHigh", ctypes.c_size_t),
        ("Offset", wintypes.DWORD),
        ("OffsetHigh", wintypes.DWORD),
        ("hEvent", wintypes.HANDLE),
    ]


_hid.HidD_GetHidGuid.argtypes = [ctypes.POINTER(GUID)]
_hid.HidD_GetHidGuid.restype = None
_hid.HidD_GetAttributes.argtypes = [wintypes.HANDLE, ctypes.POINTER(HIDD_ATTRIBUTES)]
_hid.HidD_GetAttributes.restype = wintypes.BOOLEAN
_hid.HidD_GetProductString.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.ULONG]
_hid.HidD_GetProductString.restype = wintypes.BOOLEAN
_hid.HidD_GetPreparsedData.argtypes = [wintypes.HANDLE, ctypes.POINTER(ctypes.c_void_p)]
_hid.HidD_GetPreparsedData.restype = wintypes.BOOLEAN
_hid.HidD_FreePreparsedData.argtypes = [ctypes.c_void_p]
_hid.HidD_FreePreparsedData.restype = wintypes.BOOLEAN
_hid.HidP_GetCaps.argtypes = [ctypes.c_void_p, ctypes.POINTER(HIDP_CAPS)]
_hid.HidP_GetCaps.restype = ctypes.c_long

_setupapi.SetupDiGetClassDevsW.argtypes = [
    ctypes.POINTER(GUID), wintypes.LPCWSTR, wintypes.HWND, wintypes.DWORD,
]
_setupapi.SetupDiGetClassDevsW.restype = wintypes.HANDLE
_setupapi.SetupDiEnumDeviceInterfaces.argtypes = [
    wintypes.HANDLE, ctypes.c_void_p, ctypes.POINTER(GUID), wintypes.DWORD,
    ctypes.POINTER(SP_DEVICE_INTERFACE_DATA),
]
_setupapi.SetupDiEnumDeviceInterfaces.restype = wintypes.BOOL
_setupapi.SetupDiGetDeviceInterfaceDetailW.argtypes = [
    wintypes.HANDLE, ctypes.POINTER(SP_DEVICE_INTERFACE_DATA), ctypes.c_void_p, wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p,
]
_setupapi.SetupDiGetDeviceInterfaceDetailW.restype = wintypes.BOOL
_setupapi.SetupDiDestroyDeviceInfoList.argtypes = [wintypes.HANDLE]
_setupapi.SetupDiDestroyDeviceInfoList.restype = wintypes.BOOL

_kernel32.CreateFileW.argtypes = [
    wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD,
    wintypes.DWORD, wintypes.HANDLE,
]
_kernel32.CreateFileW.restype = wintypes.HANDLE
_kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
_kernel32.CloseHandle.restype = wintypes.BOOL
_kernel32.CreateEventW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR]
_kernel32.CreateEventW.restype = wintypes.HANDLE
_kernel32.ResetEvent.argtypes = [wintypes.HANDLE]
_kernel32.ResetEvent.restype = wintypes.BOOL
_kernel32.ReadFile.argtypes = [
    wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD),
    ctypes.POINTER(OVERLAPPED),
]
_kernel32.ReadFile.restype = wintypes.BOOL
_kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
_kernel32.WaitForSingleObject.restype = wintypes.DWORD
_kernel32.GetOverlappedResult.argtypes = [
    wintypes.HANDLE, ctypes.POINTER(OVERLAPPED), ctypes.POINTER(wintypes.DWORD), wintypes.BOOL,
]
_kernel32.GetOverlappedResult.restype = wintypes.BOOL
_kernel32.CancelIo.argtypes = [wintypes.HANDLE]
_kernel32.CancelIo.restype = wintypes.BOOL


class HidError(OSError):
    pass


def _raise(what: str):
    err = ctypes.get_last_error()
    raise HidError(err, f"{what} failed: {ctypes.FormatError(err).strip()} ({err})")


@dataclass
class DeviceInfo:
    path: str
    vendor_id: int
    product_id: int
    product: str
    usage_page: int
    usage: int
    input_report_length: int


def _open(path: str, access: int, overlapped: bool) -> int:
    flags = FILE_FLAG_OVERLAPPED if overlapped else 0
    handle = _kernel32.CreateFileW(
        path, access, FILE_SHARE_READ | FILE_SHARE_WRITE, None, OPEN_EXISTING, flags, None
    )
    if handle == INVALID_HANDLE_VALUE or handle is None:
        _raise(f"CreateFile({path})")
    return handle


def _device_paths():
    guid = GUID()
    _hid.HidD_GetHidGuid(ctypes.byref(guid))
    info_set = _setupapi.SetupDiGetClassDevsW(
        ctypes.byref(guid), None, None, DIGCF_PRESENT | DIGCF_DEVICEINTERFACE
    )
    if info_set == INVALID_HANDLE_VALUE:
        _raise("SetupDiGetClassDevs")
    try:
        index = 0
        while True:
            data = SP_DEVICE_INTERFACE_DATA()
            data.cbSize = ctypes.sizeof(SP_DEVICE_INTERFACE_DATA)
            if not _setupapi.SetupDiEnumDeviceInterfaces(
                info_set, None, ctypes.byref(guid), index, ctypes.byref(data)
            ):
                if ctypes.get_last_error() == ERROR_NO_MORE_ITEMS:
                    return
                _raise("SetupDiEnumDeviceInterfaces")
            index += 1

            required = wintypes.DWORD()
            _setupapi.SetupDiGetDeviceInterfaceDetailW(
                info_set, ctypes.byref(data), None, 0, ctypes.byref(required), None
            )
            buf = ctypes.create_string_buffer(required.value)
            # SP_DEVICE_INTERFACE_DETAIL_DATA_W.cbSize: 8 on 64-bit, 6 on 32-bit
            cb_size = 8 if ctypes.sizeof(ctypes.c_void_p) == 8 else 6
            ctypes.memmove(buf, ctypes.byref(wintypes.DWORD(cb_size)), 4)
            if not _setupapi.SetupDiGetDeviceInterfaceDetailW(
                info_set, ctypes.byref(data), buf, required, None, None
            ):
                continue
            yield ctypes.wstring_at(ctypes.addressof(buf) + 4)
    finally:
        _setupapi.SetupDiDestroyDeviceInfoList(info_set)


def _describe(path: str) -> DeviceInfo | None:
    try:
        handle = _open(path, 0, False)  # access 0: query only, works even for keyboards/mice
    except HidError:
        return None
    try:
        attrs = HIDD_ATTRIBUTES()
        attrs.Size = ctypes.sizeof(HIDD_ATTRIBUTES)
        if not _hid.HidD_GetAttributes(handle, ctypes.byref(attrs)):
            return None
        name = ctypes.create_unicode_buffer(128)
        product = name.value if _hid.HidD_GetProductString(handle, name, ctypes.sizeof(name)) else ""
        caps = HIDP_CAPS()
        preparsed = ctypes.c_void_p()
        if _hid.HidD_GetPreparsedData(handle, ctypes.byref(preparsed)):
            try:
                if _hid.HidP_GetCaps(preparsed, ctypes.byref(caps)) != HIDP_STATUS_SUCCESS:
                    caps = HIDP_CAPS()
            finally:
                _hid.HidD_FreePreparsedData(preparsed)
        return DeviceInfo(
            path, attrs.VendorID, attrs.ProductID, product,
            caps.UsagePage, caps.Usage, caps.InputReportByteLength,
        )
    finally:
        _kernel32.CloseHandle(handle)


def enumerate_devices(vendor_id: int | None = None, product_id: int | None = None) -> list[DeviceInfo]:
    result = []
    for path in _device_paths():
        info = _describe(path)
        if info is None:
            continue
        if vendor_id is not None and info.vendor_id != vendor_id:
            continue
        if product_id is not None and info.product_id != product_id:
            continue
        result.append(info)
    return result


class HidDevice:
    """An open HID device. read() waits with a timeout, so a reader thread can stop cleanly."""

    def __init__(self, info: DeviceInfo):
        self.info = info
        try:
            self._handle = _open(info.path, GENERIC_READ | GENERIC_WRITE, True)
        except HidError:  # read-only is enough: the xPress has no output reports
            self._handle = _open(info.path, GENERIC_READ, True)
        self._event = _kernel32.CreateEventW(None, True, False, None)
        self._overlapped = OVERLAPPED()
        self._overlapped.hEvent = self._event
        self._buffer = ctypes.create_string_buffer(max(1, info.input_report_length))
        self._pending = False

    def read(self, timeout_ms: int = 100) -> bytes | None:
        """One input report (including the report ID byte), or None on timeout.
        Raises HidError if the device is unplugged."""
        if not self._pending:
            _kernel32.ResetEvent(self._event)
            n = wintypes.DWORD()
            if _kernel32.ReadFile(
                self._handle, self._buffer, len(self._buffer), ctypes.byref(n),
                ctypes.byref(self._overlapped),
            ):
                return self._buffer.raw[: n.value]
            if ctypes.get_last_error() != ERROR_IO_PENDING:
                _raise("ReadFile")
            self._pending = True

        status = _kernel32.WaitForSingleObject(self._event, timeout_ms)
        if status == WAIT_TIMEOUT:
            return None
        if status != WAIT_OBJECT_0:
            _raise("WaitForSingleObject")
        self._pending = False
        n = wintypes.DWORD()
        if not _kernel32.GetOverlappedResult(
            self._handle, ctypes.byref(self._overlapped), ctypes.byref(n), False
        ):
            _raise("GetOverlappedResult")
        return self._buffer.raw[: n.value]

    def close(self):
        if self._handle:
            if self._pending:
                _kernel32.CancelIo(self._handle)
                n = wintypes.DWORD()
                _kernel32.GetOverlappedResult(  # wait for the cancel before freeing the buffer
                    self._handle, ctypes.byref(self._overlapped), ctypes.byref(n), True
                )
                self._pending = False
            _kernel32.CloseHandle(self._handle)
            _kernel32.CloseHandle(self._event)
            self._handle = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
