import re
import json
import time
import shutil
import socket
import platform
import threading
import subprocess
from pathlib import Path
from typing import Optional, Any, List, Dict, Tuple

import psutil

from .smbios import SMBIOS, SMBIOSMemoryDevice

class SystemInfo:
    """
    Collects information about the machine this process runs on.

    Every value that cannot be determined on the current platform is None.
    Capacities and traffic are in bits, frequencies in GHz, temperatures in °C,
    usage ratios in 0.0 ~ 1.0.

    snapshot() blocks for `sample_interval` seconds to measure CPU usage,
    and returns a cached result for `ttl` seconds after that.
    """

    BITS_PER_BYTE: int = 8

    # SMBIOS System Enclosure / Chassis Types (DMTF DSP0134, 7.4.1)
    CHASSIS_LAPTOP: Tuple[int, ...] = (8, 9, 10, 11, 14, 30, 31, 32)   # Portable, Laptop, Notebook, Hand Held, Sub Notebook, Tablet, Convertible, Detachable
    CHASSIS_DESKTOP: Tuple[int, ...] = (3, 4, 5, 6, 7, 13, 15, 16, 35, 36)  # Desktop, Low Profile Desktop, Pizza Box, Mini Tower, Tower, All in One, Space-saving, Lunch Box, Mini PC, Stick PC

    # Linux hwmon drivers that report CPU temperatures
    CPU_SENSORS: Tuple[str, ...] = ("coretemp", "k10temp", "zenpower", "cpu_thermal")

    def __init__(self, ttl: float = 1.0, sample_interval: float = 0.25) -> None:
        self.ttl = ttl
        self.sample_interval = sample_interval

        self.lock = threading.Lock()
        self.cache: Optional[Dict[str, Any]] = None
        self.cached_at: float = 0.0

        self.kernel_type: str = platform.system().lower()
        self.static: Dict[str, Any] = {
            "name": SystemInfo.read_hostname(),
            "type": self.read_type(),
            "kernel": {
                "type": self.kernel_type,
                "version": platform.release() or None,
            },
            "distribution": self.read_distribution(),
        }
        self.cpu_name: Optional[str] = self.read_cpu_name()
        self.cpu_base_frequency: Optional[float] = self.read_cpu_base_frequency()
        self.ram_slots: Optional[List[Dict[str, Any]]] = self.read_ram_slots()

    def snapshot(self) -> Dict[str, Any]:
        with self.lock:
            if self.cache is None or time.monotonic() - self.cached_at >= self.ttl:
                self.cache = {
                    **self.static,
                    "hardwares": {
                        "cpu": self.cpus(),
                        "ram": self.rams(),
                        "gpu": self.gpus(),
                        "network": self.networks(),
                        "storage": self.storages(),
                    },
                }
                self.cached_at = time.monotonic()
            return self.cache

    # System

    @staticmethod
    def read_hostname() -> Optional[str]:
        return socket.gethostname() or None

    def read_type(self) -> Optional[str]:
        chassis = SystemInfo.read_int(Path("/sys/class/dmi/id/chassis_type"))
        if chassis in SystemInfo.CHASSIS_LAPTOP:
            return "laptop"
        if chassis in SystemInfo.CHASSIS_DESKTOP:
            return "desktop"
        try:
            if psutil.sensors_battery() is not None:
                return "laptop"
        except (AttributeError, OSError, NotImplementedError):
            pass
        return None

    def read_distribution(self) -> Dict[str, Optional[str]]:
        name: Optional[str] = None
        version: Optional[str] = None

        if self.kernel_type == "linux":
            try:
                release = platform.freedesktop_os_release()
                name = release.get("NAME")
                version = release.get("VERSION_ID")
            except OSError:
                pass
        elif self.kernel_type == "darwin":
            name = "macOS"
            version = platform.mac_ver()[0] or None
        elif self.kernel_type == "windows":
            name = "Windows"
            version = platform.release() or None
        else:
            # BSDs, illumos, AIX, ...: the kernel is the product.
            name = platform.system() or None
            version = platform.release() or None

        return {"name": name, "version": version.split(".")[0] if version else None}

    # CPU

    def read_cpu_name(self) -> Optional[str]:
        if self.kernel_type == "linux":
            try:
                with open("/proc/cpuinfo", "r", encoding="utf-8") as f:
                    for line in f:
                        key, _, value = line.partition(":")
                        if key.strip() == "model name":
                            return value.strip() or None
            except OSError:
                pass
        elif self.kernel_type == "darwin":
            try:
                result = subprocess.run(["/usr/sbin/sysctl", "-n", "machdep.cpu.brand_string"], text=True, capture_output=True, timeout=5)
                return result.stdout.strip() or None
            except (OSError, subprocess.SubprocessError):
                pass
        return None

    def read_cpu_base_frequency(self) -> Optional[float]:
        khz = SystemInfo.read_int(Path("/sys/devices/system/cpu/cpu0/cpufreq/base_frequency"))
        return khz / 1_000_000 if khz is not None else None

    def read_cpu_current_frequency(self) -> Optional[float]:
        # psutil cannot read the clock on Apple Silicon and returns a meaningless value there.
        if self.kernel_type == "darwin":
            return None
        try:
            frequency = psutil.cpu_freq()
        except (AttributeError, OSError, NotImplementedError):
            return None
        return frequency.current / 1000 if frequency and frequency.current else None

    def read_cpu_temperatures(self) -> Tuple[List[float], Dict[int, float]]:
        try:
            sensors = psutil.sensors_temperatures()
        except (AttributeError, OSError, NotImplementedError):
            return [], {}

        for driver in SystemInfo.CPU_SENSORS:
            entries = sensors.get(driver)
            if not entries:
                continue
            cores: Dict[int, float] = {}
            for entry in entries:
                match = re.fullmatch(r"Core (\d+)", entry.label or "")
                if match:
                    cores[int(match.group(1))] = entry.current
            readings = list(cores.values()) or [entry.current for entry in entries]
            return readings, cores
        return [], {}

    def read_total_threads(self) -> Optional[int]:
        # /proc/loadavg: "0.00 0.01 0.05 running/total last_pid", where total counts every thread.
        try:
            return int(Path("/proc/loadavg").read_text(encoding="ascii").split()[3].split("/")[1])
        except (OSError, IndexError, ValueError):
            pass
        total = 0
        for process in psutil.process_iter(["num_threads"]):
            total += process.info.get("num_threads") or 0
        return total or None

    def cpus(self) -> List[Dict[str, Any]]:
        usages: List[float] = [percent / 100 for percent in psutil.cpu_percent(interval=self.sample_interval, percpu=True)]
        temperatures, temperature_cores = self.read_cpu_temperatures()

        return [{
            "name": self.cpu_name,
            "cores": psutil.cpu_count(logical=False),
            "threads": psutil.cpu_count(logical=True),
            "usage": {
                "average": sum(usages) / len(usages) if usages else None,
                "minimum": min(usages) if usages else None,
                "maximum": max(usages) if usages else None,
                "process": len(psutil.pids()),
                "threads": self.read_total_threads(),
                "cores": dict(enumerate(usages)) if usages else None,
            },
            "frequency": {
                "base": self.cpu_base_frequency,
                "current": self.read_cpu_current_frequency(),
            },
            "temperature": {
                "average": sum(temperatures) / len(temperatures) if temperatures else None,
                "minimum": min(temperatures) if temperatures else None,
                "maximum": max(temperatures) if temperatures else None,
                "cores": temperature_cores or None,
            },
        }]

    # RAM

    def rams(self) -> Dict[str, Any]:
        bits = SystemInfo.BITS_PER_BYTE
        memory = psutil.virtual_memory()
        cached: Optional[int] = getattr(memory, "cached", None)
        swap = psutil.swap_memory()

        return {
            "usage": {
                "total": memory.total * bits,
                "used": memory.used * bits,
                "available": memory.available * bits,
                "cache": cached * bits if cached is not None else None,
                "free": memory.free * bits,
            },
            "swap": {
                "total": swap.total * bits,
                "used": swap.used * bits,
                "free": swap.free * bits,
            } if swap.total > 0 else None,
            "slots": self.ram_slots,
        }

    def read_ram_slots(self) -> Optional[List[Dict[str, Any]]]:
        # Sources in order of preference. Each returns None when it is unavailable here.
        if self.kernel_type == "linux":
            return SystemInfo.read_ram_slots_smbios() or SystemInfo.read_ram_slots_udev()
        if self.kernel_type == "darwin":
            return SystemInfo.read_ram_slots_system_profiler()
        return None

    @staticmethod
    def ram_slot(locator: Optional[str], type: Optional[str], manufacturer: Optional[str], installed: bool, speed: Optional[float], size: Optional[int]) -> Dict[str, Any]:
        return {
            "locator": locator,
            "type": type,
            "manufacturer": manufacturer if installed else None,
            "free": not installed,
            "speed": speed if installed else 0.0,                                                       # MT/s
            "capacity": (size * SystemInfo.BITS_PER_BYTE if size is not None else None) if installed else 0,  # bits
        }

    @staticmethod
    def read_ram_slots_smbios() -> Optional[List[Dict[str, Any]]]:
        # Raw SMBIOS table: needs root, and is hidden inside unprivileged containers.
        structures = SMBIOS.read()
        if structures is None:
            return None

        slots: List[Dict[str, Any]] = []
        for structure in structures:
            if structure.type != SMBIOSMemoryDevice.TYPE:
                continue
            device = SMBIOSMemoryDevice.from_structure(structure)
            speed = device.configured_speed or device.speed
            slots.append(SystemInfo.ram_slot(device.locator, device.type, device.manufacturer, device.installed, float(speed) if speed else None, device.size))
        return slots or None

    @staticmethod
    def read_ram_slots_udev() -> Optional[List[Dict[str, Any]]]:
        # systemd-udevd decodes the SMBIOS table as root (rules.d/70-memory.rules, dmi_memory_id)
        # and stores the result on the dmi device, where any user can read it.
        udevadm = shutil.which("udevadm")
        if udevadm is None:
            return None
        try:
            result = subprocess.run([udevadm, "info", "--query=property", "--path=/sys/class/dmi/id"], text=True, capture_output=True, timeout=5)
        except (OSError, subprocess.SubprocessError):
            return None
        if result.returncode != 0:
            return None

        properties: Dict[str, str] = {}
        for line in result.stdout.splitlines():
            key, separator, value = line.partition("=")
            if separator:
                properties[key] = value

        try:
            count = int(properties["MEMORY_ARRAY_NUM_DEVICES"])
        except (KeyError, ValueError):
            return None

        def number(key: str) -> Optional[int]:
            try:
                value = int(properties[key])
            except (KeyError, ValueError):
                return None
            # dmi_memory_id prints a speed of 0xFFFF as is, which means "see the extended field" (not exported).
            return value if value != 0xFFFF or not key.endswith("_MTS") else None

        slots: List[Dict[str, Any]] = []
        for index in range(count):
            prefix = f"MEMORY_DEVICE_{index}_"
            type = properties.get(prefix + "TYPE")
            speed = number(prefix + "CONFIGURED_SPEED_MTS") or number(prefix + "SPEED_MTS")
            slots.append(SystemInfo.ram_slot(
                locator=properties.get(prefix + "LOCATOR"),
                type=type if type not in (None, "Unknown", "Reserved", "<OUT OF SPEC>") else None,
                manufacturer=properties.get(prefix + "MANUFACTURER"),
                installed=properties.get(prefix + "PRESENT") != "0",
                speed=float(speed) if speed else None,
                size=number(prefix + "SIZE"),
            ))
        return slots or None

    @staticmethod
    def read_ram_slots_system_profiler() -> Optional[List[Dict[str, Any]]]:
        try:
            result = subprocess.run(["/usr/sbin/system_profiler", "SPMemoryDataType", "-json"], text=True, capture_output=True, timeout=30)
            groups = json.loads(result.stdout).get("SPMemoryDataType") or []
        except (OSError, subprocess.SubprocessError, ValueError, AttributeError):
            return None

        slots: List[Dict[str, Any]] = []
        for group in groups:
            # Macs with DIMMs list each slot under "_items"; Apple silicon reports the on-package memory as one entry.
            for item in group.get("_items") or [group]:
                size_text = str(item.get("dimm_size") or item.get("SPMemoryDataType") or "")
                installed = item.get("dimm_status", "ok") != "empty" and size_text.lower() != "empty"
                speed = SystemInfo.parse_number(str(item.get("dimm_speed") or ""))
                type = item.get("dimm_type")
                slots.append(SystemInfo.ram_slot(
                    locator=item.get("_name") if "_items" in group else None,
                    type=type if type and type.lower() not in ("empty", "unknown") else None,
                    manufacturer=item.get("dimm_manufacturer"),
                    installed=installed,
                    speed=speed,
                    size=SystemInfo.parse_size(size_text),
                ))
        return slots or None

    @staticmethod
    def parse_number(text: str) -> Optional[float]:
        match = re.search(r"\d+(?:\.\d+)?", text)
        return float(match.group(0)) if match else None

    @staticmethod
    def parse_size(text: str) -> Optional[int]:
        # "32 GB" (binary units, as macOS reports memory sizes) -> bytes
        match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*(KB|MB|GB|TB)\s*", text, re.IGNORECASE)
        if not match:
            return None
        exponent = ("KB", "MB", "GB", "TB").index(match.group(2).upper()) + 1
        return int(float(match.group(1)) * 1024 ** exponent)

    # GPU

    def gpus(self) -> List[Dict[str, Any]]:
        # Linux DRM sysfs. amdgpu exposes every field; other drivers expose a subset or none.
        gpus: List[Dict[str, Any]] = []
        drm = Path("/sys/class/drm")
        if not drm.is_dir():
            return gpus

        for card in sorted(drm.iterdir(), key=lambda path: path.name):
            if not re.fullmatch(r"card\d+", card.name):
                continue
            device = card / "device"
            busy = SystemInfo.read_int(device / "gpu_busy_percent")
            gpus.append({
                "name": SystemInfo.read_text(device / "product_name"),
                "usage": busy / 100 if busy is not None else None,
                "temperature": SystemInfo.read_gpu_temperature(device),
                "vram": {
                    "usage": {
                        "shared": SystemInfo.read_vram(device, "gtt"),
                        "dedicated": SystemInfo.read_vram(device, "vram"),
                    }
                }
            })

        return gpus

    @staticmethod
    def read_gpu_temperature(device: Path) -> Optional[float]:
        for sensor in sorted(device.glob("hwmon/hwmon*/temp1_input")):
            millidegrees = SystemInfo.read_int(sensor)
            if millidegrees is not None:
                return millidegrees / 1000
        return None

    @staticmethod
    def read_vram(device: Path, kind: str) -> Dict[str, Optional[int]]:
        bits = SystemInfo.BITS_PER_BYTE
        total = SystemInfo.read_int(device / f"mem_info_{kind}_total")
        used = SystemInfo.read_int(device / f"mem_info_{kind}_used")
        return {
            "total": total * bits if total is not None else None,
            "used": used * bits if used is not None else None,
            "free": (total - used) * bits if total is not None and used is not None else None,
        }

    # Network

    def networks(self) -> List[Dict[str, Any]]:
        bits = SystemInfo.BITS_PER_BYTE
        counters = psutil.net_io_counters(pernic=True)

        networks: List[Dict[str, Any]] = []
        for name, stats in psutil.net_if_stats().items():
            if "loopback" in stats.flags.split(","):
                continue
            io = counters.get(name)
            networks.append({
                "name": name,
                "up": stats.isup,
                "speed": stats.speed * 1_000_000 if stats.speed else None,  # bits/s
                "mtu": stats.mtu,
                "traffic": {
                    "sent": io.bytes_sent * bits if io else None,
                    "received": io.bytes_recv * bits if io else None,
                },
                "packets": {
                    "sent": io.packets_sent if io else None,
                    "received": io.packets_recv if io else None,
                },
                "errors": {
                    "sent": io.errout if io else None,
                    "received": io.errin if io else None,
                },
                "drops": {
                    "sent": io.dropout if io else None,
                    "received": io.dropin if io else None,
                },
            })

        return networks

    # Storage

    def storages(self) -> List[Dict[str, Any]]:
        bits = SystemInfo.BITS_PER_BYTE
        try:
            counters = psutil.disk_io_counters(perdisk=True) or {}
        except (OSError, RuntimeError):
            counters = {}

        storages: Dict[str, Dict[str, Any]] = {}
        for partition in psutil.disk_partitions(all=False):
            if partition.device in storages:
                storages[partition.device]["mountpoints"].append(partition.mountpoint)
                continue

            try:
                usage = psutil.disk_usage(partition.mountpoint)
                usage_info: Optional[Dict[str, int]] = {"total": usage.total * bits, "used": usage.used * bits, "free": usage.free * bits}
            except OSError:
                usage_info = None

            io = counters.get(Path(partition.device).name)
            storages[partition.device] = {
                "device": partition.device,
                "filesystem": partition.fstype or None,
                "mountpoints": [partition.mountpoint],
                "usage": usage_info,
                "io": {
                    "read": io.read_bytes * bits if io else None,
                    "written": io.write_bytes * bits if io else None,
                },
            }

        return list(storages.values())

    # Files

    @staticmethod
    def read_text(path: Path) -> Optional[str]:
        try:
            return path.read_text(encoding="utf-8").strip() or None
        except (OSError, UnicodeDecodeError):
            return None

    @staticmethod
    def read_int(path: Path) -> Optional[int]:
        text = SystemInfo.read_text(path)
        try:
            return int(text) if text is not None else None
        except ValueError:
            return None
