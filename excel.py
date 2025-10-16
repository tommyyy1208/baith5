import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pyautogui
import time
import threading
import keyboard
import json
import copy

click_sets = {}  # {'Tên bộ': [{'name': 'Tên vị trí', 'x': x, 'y': y}, ...]}
is_clicking = False  # Dùng để dừng khi nhấn F9

# Lấy bộ đang chọn
def get_current_set():
    return set_selector.get()

# Lắng nghe phím F8 để thêm vị trí
def listen_for_hotkeys():
    while True:
        keyboard.wait('F8')
        x, y = pyautogui.position()
        current_set = get_current_set()
        if current_set:
            name = position_name_entry.get().strip()
            if not name:
                name = f"Vị trí {len(click_sets[current_set]) + 1}"
            click_sets[current_set].append({"name": name, "x": x, "y": y})
            if get_current_set() == current_set:
                update_position_list()
        else:
            messagebox.showwarning("Chưa chọn bộ", "Hãy chọn hoặc tạo một bộ nhấp trước.")

# Lắng nghe phím F9 để dừng auto click
def listen_for_stop():
    global is_clicking
    while True:
        keyboard.wait('F9')
        is_clicking = False

# Bắt đầu click
def start_clicking():
    global is_clicking
    current_set = get_current_set()
    if not current_set or current_set not in click_sets:
        messagebox.showwarning("Lỗi", "Vui lòng chọn một bộ nhấp hợp lệ.")
        return

    try:
        delay = float(delay_entry.get())
        repeat = int(repeat_entry.get())
    except ValueError:
        messagebox.showerror("Lỗi", "Delay và số lần lặp phải là số.")
        return

    if not click_sets[current_set]:
        messagebox.showinfo("Trống", "Bộ nhấp hiện tại không có vị trí nào.")
        return

    is_clicking = True

    def click_loop():
        nonlocal repeat
        for r in range(repeat):
            if not is_clicking:
                break
            for item in click_sets[current_set]:
                if not is_clicking:
                    break
                x = item.get("x", 0)
                y = item.get("y", 0)
                pyautogui.click(x, y)
                time.sleep(delay)
        print("Kết thúc auto click.")

    threading.Thread(target=click_loop, daemon=True).start()

# Tạo bộ nhấp mới
def create_new_set():
    name = new_set_entry.get().strip()
    if not name:
        messagebox.showerror("Lỗi", "Tên bộ không được để trống.")
        return
    if name in click_sets:
        messagebox.showwarning("Tồn tại", "Bộ nhấp đã tồn tại.")
        return

    current_set = get_current_set()
    if copy_from_current_var.get() and current_set in click_sets:
        click_sets[name] = copy.deepcopy(click_sets[current_set])
    else:
        click_sets[name] = []

    update_set_selector()
    set_selector.set(name)
    update_position_list()
    new_set_entry.delete(0, tk.END)

# Xoá bộ nhấp
def delete_set():
    current = get_current_set()
    if not current:
        return
    if messagebox.askyesno("Xác nhận", f"Xóa bộ '{current}'?"):
        click_sets.pop(current, None)
        update_set_selector()
        position_list.delete(0, tk.END)

# Xoá các vị trí đã chọn trong danh sách
def delete_selected_positions():
    current = get_current_set()
    if current not in click_sets:
        return

    selected_indices = list(position_list.curselection())
    if not selected_indices:
        messagebox.showinfo("Chưa chọn", "Vui lòng chọn vị trí cần xoá.")
        return

    for index in reversed(selected_indices):
        try:
            del click_sets[current][index]
        except IndexError:
            continue

    update_position_list()

# Cập nhật danh sách vị trí hiển thị
def update_position_list(event=None):
    position_list.delete(0, tk.END)
    current = get_current_set()
    if current in click_sets:
        for item in click_sets[current]:
            name = item.get("name", "Không tên")
            x = item.get("x", 0)
            y = item.get("y", 0)
            position_list.insert(tk.END, f"{name} - ({x}, {y})")

# Cập nhật combobox chọn bộ
def update_set_selector():
    set_selector['values'] = list(click_sets.keys())
    if click_sets:
        set_selector.set(list(click_sets.keys())[0])
    else:
        set_selector.set('')
    update_position_list()

# Lưu ra file JSON
def save_to_file():
    path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
    if path:
        with open(path, 'w') as f:
            json.dump(click_sets, f, indent=2)
        messagebox.showinfo("Đã lưu", "Dữ liệu đã được lưu.")

# Mở file JSON
def load_from_file():
    path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
    if path:
        try:
            with open(path, 'r') as f:
                data = json.load(f)
                global click_sets
                click_sets = {k: v for k, v in data.items() if isinstance(v, list)}
                update_set_selector()
                messagebox.showinfo("Thành công", "Tải dữ liệu thành công.")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể đọc file: {e}")

# ================= GUI =================
root = tk.Tk()
root.title("🖱️ Auto Clicker Nâng Cao (F8: Thêm, F9: Dừng)")
root.geometry("500x720")

# --- Tạo/Xoá bộ ---
tk.Label(root, text="Tên bộ nhấp mới:").pack()
new_set_entry = tk.Entry(root)
new_set_entry.pack(pady=5)

# ✅ Checkbox: sao chép từ bộ hiện tại
copy_from_current_var = tk.BooleanVar()
tk.Checkbutton(root, text="✅ Sao chép vị trí từ bộ hiện tại", variable=copy_from_current_var).pack()

tk.Button(root, text="➕ Tạo bộ mới", command=create_new_set).pack(pady=2)
tk.Button(root, text="🗑️ Xoá bộ hiện tại", command=delete_set).pack(pady=2)

# --- Chọn bộ ---
tk.Label(root, text="Chọn bộ nhấp:").pack()
set_selector = ttk.Combobox(root, state="readonly")
set_selector.pack(pady=5)
set_selector.bind("<<ComboboxSelected>>", update_position_list)

# --- Nhập tên vị trí ---
tk.Label(root, text="Tên vị trí mới:").pack()
position_name_entry = tk.Entry(root)
position_name_entry.pack(pady=5)

# --- Danh sách vị trí ---
position_list = tk.Listbox(root, width=50, height=10, selectmode=tk.MULTIPLE)
position_list.pack(pady=5)
tk.Button(root, text="❌ Xoá vị trí đã chọn", command=delete_selected_positions).pack(pady=2)

# --- Delay và lặp lại ---
tk.Label(root, text="Delay giữa các click (giây):").pack()
delay_entry = tk.Entry(root)
delay_entry.insert(0, "0.5")
delay_entry.pack(pady=2)

tk.Label(root, text="Số lần lặp lại toàn bộ bộ nhấp:").pack()
repeat_entry = tk.Entry(root)
repeat_entry.insert(0, "1")
repeat_entry.pack(pady=2)

# --- Nút thao tác ---
tk.Button(root, text="▶️ Bắt đầu Click", command=start_clicking).pack(pady=10)

tk.Label(root, text="💡 Nhấn F8 để thêm vị trí chuột.\n⛔ Nhấn F9 để dừng auto click.", fg="gray").pack(pady=5)

# --- Lưu / Mở file ---
tk.Button(root, text="💾 Lưu bộ nhấp ra file", command=save_to_file).pack(pady=2)
tk.Button(root, text="📂 Mở file bộ nhấp", command=load_from_file).pack(pady=2)

# --- Khởi chạy luồng lắng nghe phím nóng ---
threading.Thread(target=listen_for_hotkeys, daemon=True).start()
threading.Thread(target=listen_for_stop, daemon=True).start()

root.mainloop()
