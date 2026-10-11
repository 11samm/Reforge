"""Windows child lifetime bound to the job owner, including abrupt host interruption."""
import os

class OwnedTree:
    def __init__(self,process):
        self.handle=None
        if os.name!='nt': return
        import ctypes
        from ctypes import wintypes as W
        class BASIC(ctypes.Structure):
            _fields_=[('PerProcessUserTimeLimit',ctypes.c_longlong),('PerJobUserTimeLimit',ctypes.c_longlong),('LimitFlags',W.DWORD),('MinimumWorkingSetSize',ctypes.c_size_t),('MaximumWorkingSetSize',ctypes.c_size_t),('ActiveProcessLimit',W.DWORD),('Affinity',ctypes.c_size_t),('PriorityClass',W.DWORD),('SchedulingClass',W.DWORD)]
        class IO(ctypes.Structure):
            _fields_=[(n,ctypes.c_ulonglong) for n in ('ReadOperationCount','WriteOperationCount','OtherOperationCount','ReadTransferCount','WriteTransferCount','OtherTransferCount')]
        class EXTENDED(ctypes.Structure):
            _fields_=[('BasicLimitInformation',BASIC),('IoInfo',IO),('ProcessMemoryLimit',ctypes.c_size_t),('JobMemoryLimit',ctypes.c_size_t),('PeakProcessMemoryUsed',ctypes.c_size_t),('PeakJobMemoryUsed',ctypes.c_size_t)]
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.CreateJobObjectW.argtypes=[ctypes.c_void_p,W.LPCWSTR]; kernel.CreateJobObjectW.restype=W.HANDLE
        kernel.SetInformationJobObject.argtypes=[W.HANDLE,ctypes.c_int,ctypes.c_void_p,W.DWORD]; kernel.SetInformationJobObject.restype=W.BOOL
        kernel.AssignProcessToJobObject.argtypes=[W.HANDLE,W.HANDLE]; kernel.AssignProcessToJobObject.restype=W.BOOL
        kernel.CloseHandle.argtypes=[W.HANDLE]; kernel.CloseHandle.restype=W.BOOL
        handle=kernel.CreateJobObjectW(None,None)
        if not handle: raise ctypes.WinError(ctypes.get_last_error())
        limits=EXTENDED(); limits.BasicLimitInformation.LimitFlags=0x2000 # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not kernel.SetInformationJobObject(handle,9,ctypes.byref(limits),ctypes.sizeof(limits)) or not kernel.AssignProcessToJobObject(handle,W.HANDLE(int(process._handle))):
            error=ctypes.get_last_error(); kernel.CloseHandle(handle); raise ctypes.WinError(error)
        self.handle=handle; self.kernel=kernel
    def close(self):
        if self.handle is not None: self.kernel.CloseHandle(self.handle); self.handle=None
