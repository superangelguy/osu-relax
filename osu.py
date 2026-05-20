import re
import time
import sys
import os
import random
import keyboard
import threading
import ctypes
import ctypes.wintypes
import psutil

class OsuRelaxCheatsEngine:
    def __init__(self, osu_file_path):
        self.osu_file_path = osu_file_path
        self.slider_multiplier = 1.4  # Map default fallback configuration
        self.timing_points = []       # Tracks dynamic BPM/Velocity alterations
        self.hit_objects = []         # Ordered execution timeline
        self.is_running = False
        
        self.parse_beatmap_metadata()
        self.parse_hit_objects()

    def parse_beatmap_metadata(self):
        """Extracts overall map difficulty modifiers and structural timing blocks."""
        with open(self.osu_file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 1. Pull global SliderMultiplier setting
        sm_match = re.search(r'SliderMultiplier\s*:\s*([\d.]+)', content)
        if sm_match:
            self.slider_multiplier = float(sm_match.group(1))

        # 2. Isolate and ingest [TimingPoints]
        tp_section = re.search(r'\[TimingPoints\]\n([\s\S]*?)(?=\n\[|$)', content)
        if tp_section:
            for line in tp_section.group(1).strip().split('\n'):
                if not line.strip() or line.startswith('//'):
                    continue
                parts = line.split(',')
                if len(parts) < 2:
                    continue
                
                offset = float(parts[0])
                beat_length = float(parts[1])
                uninherited = int(parts[6]) if len(parts) > 6 else 1
                
                self.timing_points.append({
                    'time': offset,
                    'beat_length': beat_length,
                    'uninherited': bool(uninherited)
                })
        
        self.timing_points.sort(key=lambda x: x['time'])

    def get_active_timing(self, hit_time):
        """Looks backward sequentially to calculate tempo modifiers at a specific timestamp."""
        active_beat_length = 600.0  # Default 100 BPM global fallback
        velocity_multiplier = 1.0

        for tp in self.timing_points:
            if tp['time'] > hit_time:
                break
            
            if tp['uninherited']:
                active_beat_length = tp['beat_length']
                velocity_multiplier = 1.0  # Reset on a new Red Line
            else:
                if tp['beat_length'] < 0:
                    velocity_multiplier = -100.0 / tp['beat_length']
                else:
                    velocity_multiplier = 1.0

        return active_beat_length, velocity_multiplier

    def calculate_slider_duration(self, hit_time, pixel_length, repeats):
        """Applies internal native physics equations to establish exact hold milestones."""
        beat_length, velocity_mult = self.get_active_timing(hit_time)
        single_pass = (pixel_length * beat_length * (1.0 / velocity_mult)) / (self.slider_multiplier * 100.0)
        return single_pass * repeats

    def parse_hit_objects(self):
        """Builds a sequential processing timeline from map hit objects."""
        with open(self.osu_file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        ho_section = re.search(r'\[HitObjects\]\n([\s\S]*)', content)
        if not ho_section:
            print("[-] Error: Missing [HitObjects] data block.")
            return

        for line in ho_section.group(1).strip().split('\n'):
            if not line.strip() or line.startswith('//'):
                continue
            parts = line.split(',')
            if len(parts) < 4:
                continue
            
            x = int(parts[0])
            y = int(parts[1])
            timestamp = int(parts[2])
            obj_type = int(parts[3])

            is_slider = bool(obj_type & 2)
            duration = 0

            # If it's a slider, determine precise pixel distance and repeats
            if is_slider and len(parts) > 7:
                try:
                    repeats = int(parts[6])
                    pixel_length = float(parts[7])
                    duration = self.calculate_slider_duration(timestamp, pixel_length, repeats)
                except (ValueError, IndexError):
                    duration = 150  # Fallback safety default on malformed lines
            
            self.hit_objects.append({
                'time': timestamp,
                'is_slider': is_slider,
                'duration': duration
            })
            
        pass

    def run_playback_loop(self, start_key, key_1, key_2, time_reader):
        """Core execution loop with pause/fail/retry detection and humanization."""
        if hasattr(time_reader, 'anchor_now'):
            print("[*] Ready — press Z/X when you start playing")
            while self.is_running:
                if keyboard.is_pressed(key_1) or keyboard.is_pressed(key_2):
                    break
                time.sleep(0.001)
            if not self.is_running:
                return
            print("[⚡] Synced!")
            time_reader.anchor_now(self.hit_objects[0]['time'])
        else:
            print(f"\n[➔] Engine Armed. Alt-tab into osu! and press '{start_key.upper()}' when ready.")
            while self.is_running:
                if keyboard.is_pressed(start_key):
                    break
                time.sleep(0.001)
            if not self.is_running:
                return
            print("[⚡] Synchronized! Playing map timeline...")

        current_key = key_1
        next_idx = 0
        last_obj_time = self.hit_objects[-1]['time'] + self.hit_objects[-1]['duration']
        paused = False
        pause_start = 0.0
        esc_was_pressed = False

        def jitter(base_ms, spread=8):
            return base_ms + random.randint(-spread, spread)

        def tap_duration():
            return random.uniform(0.012, 0.055)

        while self.is_running and next_idx < len(self.hit_objects):
            if keyboard.is_pressed('esc'):
                if not esc_was_pressed:
                    esc_was_pressed = True
                    if not paused:
                        paused = True
                        pause_start = time.time()
                        keyboard.release(key_1)
                        keyboard.release(key_2)
                        print("[⏸] Paused")
                    else:
                        paused = False
                        if hasattr(time_reader, 'pause_state'):
                            time_reader.pause_state['offset'] += time.time() - pause_start
                        print("[▶] Resumed")
            else:
                esc_was_pressed = False

            if paused:
                time.sleep(0.05)
                continue

            game_ms = time_reader()
            if game_ms is None:
                time.sleep(0.005)
                continue

            if game_ms > last_obj_time + 5000:
                print("[!] Map ended / failed / retried")
                self.is_running = False
                return

            obj = self.hit_objects[next_idx]
            hit_time = jitter(obj['time'], spread=6)

            if game_ms >= hit_time:
                current_key = key_2 if current_key == key_1 else key_1

                if obj['is_slider']:
                    keyboard.press(current_key)
                    release_ms = jitter(obj['time'] + obj['duration'], spread=10)
                    while self.is_running and not paused:
                        if keyboard.is_pressed('esc'):
                            break
                        now = time_reader()
                        if now is None or now >= release_ms:
                            break
                        time.sleep(0.001)
                    keyboard.release(current_key)
                else:
                    keyboard.press(current_key)
                    time.sleep(tap_duration())
                    keyboard.release(current_key)

                next_idx += 1
            else:
                time.sleep(0.0005)

        if self.is_running:
            print("[+] Map complete.")
        self.is_running = False

    def start(self, time_reader, start_key='e', key_1='z', key_2='x'):
        """Spawns the loop on a dedicated thread to preserve control input stability."""
        if self.is_running:
            print("[-] Engine is already active.")
            return
        self.is_running = True
        self.worker_thread = threading.Thread(
            target=self.run_playback_loop,
            args=(start_key, key_1, key_2, time_reader),
            daemon=True
        )
        self.worker_thread.start()

    def stop(self, silent=False):
        """Immediately aborts execution loops and purges current keystates safely."""
        if self.is_running:
            if not silent:
                print("\n[-] Aborting relax automation routine gracefully...")
            self.is_running = False
            keyboard.release('z')
            keyboard.release('x')


def find_osu_process():
    """Find the osu! process and return (pid, handle) or (None, None)."""
    for proc in psutil.process_iter(['name', 'pid']):
        if proc.info['name'] and proc.info['name'].lower() == 'osu!.exe':
            pid = proc.info['pid']
            break
    else:
        return None, None

    h_process = ctypes.windll.kernel32.OpenProcess(
        0x0010 | 0x0400 | 0x0008, False, pid
    )
    if not h_process:
        return None, None
    return pid, h_process


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", ctypes.wintypes.DWORD),
        ("RegionSize", ctypes.c_size_t),
        ("State", ctypes.wintypes.DWORD),
        ("Protect", ctypes.wintypes.DWORD),
        ("Type", ctypes.wintypes.DWORD),
    ]

MEM_COMMIT = 0x1000
MEM_PRIVATE = 0x20000
PAGE_READWRITE = 0x04
PAGE_EXECUTE_READWRITE = 0x40


def find_pattern(data, pattern, mask, start=0):
    """Find a byte pattern with wildcard mask in data. Returns index or -1."""
    if len(pattern) != len(mask):
        return -1
    for i in range(start, len(data) - len(pattern) + 1):
        match = True
        for j in range(len(pattern)):
            if mask[j] == ord('x') and data[i + j] != pattern[j]:
                match = False
                break
        if match:
            return i
    return -1


def scan_osu_memory(h_process):
    """Single-pass scan of osu! memory for both game-time address and beatmap path.
    Returns (time_addr, beatmap_path) — each may be None if not found."""
    kernel32 = ctypes.windll.kernel32
    kernel32.ReadProcessMemory.argtypes = [
        ctypes.wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
        ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)
    ]
    kernel32.VirtualQueryEx.argtypes = [
        ctypes.wintypes.HANDLE, ctypes.c_void_p,
        ctypes.c_void_p, ctypes.c_size_t
    ]

    time_signature = b'\xa1\x00\x00\x00\x00\xa3\x00\x00\x00\x00\x8d'
    time_mask = b'x????x????x'
    songs_marker = 'Songs\\'.encode('utf-16-le')

    time_addr = None
    beatmap_path = None

    addr = 0
    max_addr = 0x7FFFFFFF

    while addr < max_addr:
        mbi = MEMORY_BASIC_INFORMATION()
        result = kernel32.VirtualQueryEx(
            h_process, ctypes.c_void_p(addr),
            ctypes.byref(mbi), ctypes.sizeof(mbi)
        )
        if result == 0 or mbi.BaseAddress is None:
            break

        if (mbi.State == MEM_COMMIT and
                mbi.Type == MEM_PRIVATE and
                mbi.Protect in (PAGE_READWRITE, PAGE_EXECUTE_READWRITE)):
            try:
                buf = ctypes.create_string_buffer(mbi.RegionSize)
                bytes_read = ctypes.c_size_t(0)
                if not kernel32.ReadProcessMemory(
                    h_process, mbi.BaseAddress, buf, mbi.RegionSize, ctypes.byref(bytes_read)
                ):
                    addr = mbi.BaseAddress + mbi.RegionSize
                    continue
                data = buf.raw[:bytes_read.value]
            except Exception:
                addr = mbi.BaseAddress + mbi.RegionSize
                continue

            if time_addr is None:
                pos = 0
                while True:
                    idx = find_pattern(data, time_signature, time_mask, pos)
                    if idx == -1:
                        break
                    ptr_addr = mbi.BaseAddress + idx + 6
                    val = ctypes.c_uint32()
                    if kernel32.ReadProcessMemory(
                        h_process, ctypes.c_void_p(ptr_addr),
                        ctypes.byref(val), 4, ctypes.byref(ctypes.c_size_t(0))
                    ):
                        time_addr = val.value
                        if beatmap_path is not None:
                            return time_addr, beatmap_path
                        break
                    pos = idx + 1

            if beatmap_path is None:
                pos = 0
                while True:
                    idx = data.find(songs_marker, pos)
                    if idx == -1:
                        break
                    start = data.rfind(b'\x00\x00', 0, idx)
                    start = start + 2 if start != -1 else 0
                    end = data.find('.osu\x00\x00'.encode('utf-16-le'), idx)
                    if end == -1:
                        pos = idx + len(songs_marker)
                        continue
                    end += len('.osu\x00\x00'.encode('utf-16-le'))
                    try:
                        path = data[start:end].decode('utf-16-le', errors='ignore')
                        if os.path.isfile(path):
                            beatmap_path = path
                            if time_addr is not None:
                                return time_addr, beatmap_path
                            break
                    except Exception:
                        pass
                    pos = idx + len(songs_marker)

        addr = mbi.BaseAddress + mbi.RegionSize

    return time_addr, beatmap_path


def make_time_reader(h_process, time_addr):
    """Return a closure that reads the current in-game time in milliseconds."""
    kernel32 = ctypes.windll.kernel32

    def read_time():
        val = ctypes.c_int32()
        if kernel32.ReadProcessMemory(
            h_process, ctypes.c_void_p(time_addr),
            ctypes.byref(val), 4, ctypes.byref(ctypes.c_size_t(0))
        ):
            return val.value
        return None

    return read_time


def find_recent_beatmap():
    """Find the most recently accessed .osu file in the Songs folder.
    osu! reads the .osu file when a beatmap is selected, updating its access time."""
    songs_dir = os.path.join(os.environ['LOCALAPPDATA'], 'osu!', 'Songs')
    if not os.path.isdir(songs_dir):
        return None

    best_path = None
    best_time = 0

    for root, dirs, files in os.walk(songs_dir):
        for f in files:
            if not f.lower().endswith('.osu'):
                continue
            full = os.path.join(root, f)
            try:
                atime = os.path.getatime(full)
                if atime > best_time:
                    best_time = atime
                    best_path = full
            except OSError:
                continue

    return best_path


def pick_beatmap_gui():
    """Fallback: open a file dialog to select a .osu beatmap."""
    import subprocess
    import tempfile

    ps_script = '''
Add-Type -AssemblyName System.Windows.Forms
$dialog = New-Object System.Windows.Forms.OpenFileDialog
$dialog.Filter = "osu! Beatmap (*.osu)|*.osu"
$dialog.InitialDirectory = [Environment]::GetFolderPath('LocalApplicationData') + '\\osu!\\Songs'
$dialog.Title = "Select an osu! beatmap file"
if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
    Write-Output $dialog.FileName
}
'''
    tf = tempfile.NamedTemporaryFile(mode='w', suffix='.ps1', delete=False, encoding='utf-8')
    tf.write(ps_script)
    tf.close()
    try:
        result = subprocess.run(
            ['powershell', '-ExecutionPolicy', 'Bypass', '-File', tf.name],
            capture_output=True, text=True
        )
        path = result.stdout.strip()
        return path if path else None
    finally:
        os.unlink(tf.name)


def get_osu_window_title():
    """Get the osu! window title text. Returns empty string if not found."""
    user32 = ctypes.windll.user32
    hwnd = user32.FindWindowW(None, None)
    titles = []

    def enum_callback(hwnd, lparam):
        buf = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, buf, 256)
        title = buf.value
        class_buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, class_buf, 256)
        if class_buf.value == 'WindowsForms10.Window.8.app.0.2a0a0e0_r14_ad1' or 'osu!' in title.lower():
            titles.append(title)
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    user32.EnumWindows(WNDENUMPROC(enum_callback), 0)

    for t in titles:
        if t and 'osu!' in t.lower():
            return t
    return '' if not titles else titles[0]


if __name__ == "__main__":
    print("[*] osu! Relax Monitor — watching for beatmap changes...")
    print("[*] Press 'ESC' at any time to exit.\n")

    pid, h_process = find_osu_process()
    if not h_process:
        print("[-] osu! is not running. Waiting for osu! to start...")
    else:
        print(f"[+] Connected to osu! (PID: {pid})")

    time_addr, _ = scan_osu_memory(h_process) if h_process else (None, None)
    if time_addr:
        print(f"[+] Memory sync active — game time: 0x{time_addr:08X}")
    else:
        print("[!] Using wall-clock sync (may drift slightly)")

    current_map = None
    engine = None
    pending_map = None
    pending_since = 0

    try:
        while True:
            if keyboard.is_pressed('esc'):
                break

            if not h_process:
                pid, h_process = find_osu_process()
                if h_process:
                    print(f"[+] osu! started (PID: {pid})")
                    time_addr, _ = scan_osu_memory(h_process)
                    if time_addr:
                        print(f"[+] Memory sync active — game time: 0x{time_addr:08X}")
                time.sleep(2)
                continue

            if not psutil.pid_exists(pid):
                print("[!] osu! closed. Waiting for restart...")
                if engine:
                    engine.stop()
                    engine = None
                current_map = None
                pending_map = None
                ctypes.windll.kernel32.CloseHandle(h_process)
                h_process = None
                time.sleep(2)
                continue

            recent = find_recent_beatmap()

            if recent and recent != pending_map:
                pending_map = recent
                pending_since = time.time()

            if (pending_map and pending_map != current_map and
                    time.time() - pending_since >= 2.0):
                if engine:
                    engine.stop(silent=True)
                    engine = None
                current_map = pending_map
                try:
                    engine = OsuRelaxCheatsEngine(current_map)
                    print(f"[+] {os.path.basename(current_map)} ({len(engine.hit_objects)} obj)")
                except Exception as e:
                    print(f"[-] Failed: {e}")
                    current_map = None
                    pending_map = None
                    time.sleep(2)
                    continue

                if time_addr:
                    time_reader = make_time_reader(h_process, time_addr)
                else:
                    st = {'anchored': False, 'anchor_ms': 0, 'anchor_t': 0.0}
                    pause_st = {'offset': 0.0}

                    def time_reader():
                        if not st['anchored']:
                            return 0
                        elapsed = time.time() - st['anchor_t'] - pause_st['offset']
                        return st['anchor_ms'] + int(elapsed * 1000)

                    def anchor_now(first_hit_ms):
                        st['anchor_ms'] = first_hit_ms
                        st['anchor_t'] = time.time()
                        st['anchored'] = True
                        pause_st['offset'] = 0.0

                    time_reader.anchor_now = anchor_now
                    time_reader.pause_state = pause_st

                engine.start(time_reader, start_key='e', key_1='z', key_2='x')

            if engine and not engine.is_running and current_map:
                current_map = None
                pending_map = None
                engine = None

            time.sleep(random.uniform(2.0, 4.0))

    except KeyboardInterrupt:
        pass
    finally:
        if engine:
            engine.stop()
        if h_process:
            ctypes.windll.kernel32.CloseHandle(h_process)
        print("\n[+] Exited.")
