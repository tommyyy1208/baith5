import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import openpyxl
import os
import time
import re

# ==========================
# ĐỌC FILE CLASS ĐA NGÔN NGỮ
# ==========================
def load_classes_from_file(filename="classes.txt"):
    if not os.path.exists(filename):
        messagebox.showerror("Error", f"File {filename} not found.")
        return {}, [], {}

    with open(filename, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    lang_dict = {}
    class_mapping = {}  # Ánh xạ class giữa các ngôn ngữ
    current_lang = None
    current_class_index = 0
    parent_classes = {}  # Lưu trữ class mẹ
    child_classes = []   # Lưu trữ chỉ class con

    for line in lines:
        if re.match(r"^\d+\.\s", line):  # dòng ngôn ngữ
            lang_name = line.split(". ", 1)[1]
            current_lang = lang_name
            lang_dict[current_lang] = []
            current_class_index = 0
        elif re.match(r"^\d+\.\d+\.\s", line) and current_lang:  # class mẹ
            cls_name = line.split(". ", 1)[1]
            lang_dict[current_lang].append(cls_name)
            
            # Tạo mapping cho class mẹ
            if current_class_index not in class_mapping:
                class_mapping[current_class_index] = {}
            class_mapping[current_class_index][current_lang] = cls_name
            parent_classes[current_class_index] = cls_name
            current_class_index += 1
        elif re.match(r"^\d+\.\d+\.\d+\.\s", line) and current_lang:  # class con
            cls_name = line.split(". ", 1)[1]
            lang_dict[current_lang].append(cls_name)
            
            # Tạo mapping cho class con
            if current_class_index not in class_mapping:
                class_mapping[current_class_index] = {}
            class_mapping[current_class_index][current_lang] = cls_name
            child_classes.append(current_class_index)  # Thêm vào danh sách class con
            current_class_index += 1

    languages = list(lang_dict.keys())
    return lang_dict, languages, class_mapping, parent_classes, child_classes

# Hàm validate chỉ cho phép nhập số
def validate_number_input(new_value):
    if new_value == "":
        return True
    try:
        int(new_value)
        return True
    except ValueError:
        return False

# ==========================
# ỨNG DỤNG CHÍNH
# ==========================
class CounterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Annotation Counter Tool")
        self.root.geometry("1200x800")  # Kích thước mặc định lớn hơn

        self.class_sets, self.languages, self.class_mapping, self.parent_classes, self.child_classes = load_classes_from_file()
        if not self.languages:
            messagebox.showerror("Error", "No class definitions found in classes.txt")
            self.root.destroy()
            return

        self.current_language = tk.StringVar(value=self.languages[0])

        # Tạo danh sách các class theo index
        self.class_indexes = list(self.class_mapping.keys())
        
        # Khởi tạo counts_all theo index class
        self.counts_all = {}
        for index in self.class_indexes:
            self.counts_all[index] = tk.IntVar(value=0)

        self.count_labels = {}  # Lưu trữ label hiển thị cho mỗi class
        self.entry_widgets = {}  # Lưu trữ entry widgets cho nhập số trực tiếp
        self.total_work_time = 0.0  # lưu giây
        self.session_start = None
        self.is_paused = True

        # Đăng ký hàm validate
        self.vcmd = (self.root.register(validate_number_input), '%P')

        self.setup_ui()
        self.update_timer_display()

    # ----------------------------
    # GIAO DIỆN CHÍNH
    # ----------------------------
    def setup_ui(self):
        # Main frame với scrollbar
        main_container = ttk.Frame(self.root)
        main_container.pack(fill="both", expand=True)

        # Tạo canvas và scrollbar
        self.canvas = tk.Canvas(main_container)
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Bind mouse wheel to canvas
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)

        main_frame = ttk.Frame(self.scrollable_frame, padding=10)
        main_frame.pack(fill="both", expand=True)

        # Nhập tên dữ liệu
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(pady=10, fill="x")
        ttk.Label(top_frame, text="Dataset Name:").pack(side="left")
        self.dataset_name_entry = ttk.Entry(top_frame, width=30)
        self.dataset_name_entry.pack(side="left", padx=5)

        # Chọn ngôn ngữ hiển thị
        ttk.Label(top_frame, text="Display Language:").pack(side="left", padx=(20, 5))
        lang_menu = ttk.OptionMenu(
            top_frame, self.current_language, self.languages[0], *self.languages, command=self.update_language
        )
        lang_menu.pack(side="left")

        # Nút Save và Load - ĐƯA LÊN TRÊN
        save_load_frame = ttk.Frame(main_frame)
        save_load_frame.pack(pady=10)
        ttk.Button(save_load_frame, text="💾 Save to Excel", command=self.save_to_excel).pack(side="left", padx=5)
        ttk.Button(save_load_frame, text="📂 Load from Excel", command=self.load_from_excel).pack(side="left", padx=5)

        # Hiển thị thời gian làm việc
        self.timer_label = ttk.Label(main_frame, text="Working Time: 00:00:00", font=("Arial", 11))
        self.timer_label.pack(pady=(10, 5))

        # Nút Play / Pause
        timer_controls = ttk.Frame(main_frame)
        timer_controls.pack()
        ttk.Button(timer_controls, text="▶ Play", command=self.start_timer).pack(side="left", padx=5)
        ttk.Button(timer_controls, text="⏸ Pause", command=self.pause_timer).pack(side="left", padx=5)

        # Danh sách class - chia thành 2 hàng, mỗi hàng 3 cột
        self.class_frame = ttk.Frame(main_frame)
        self.class_frame.pack(pady=10, fill="both", expand=True)

        self.update_language(self.current_language.get())

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    # ----------------------------
    # CẬP NHẬT NGÔN NGỮ HIỂN THỊ
    # ----------------------------
    def update_language(self, lang):
        # Xóa widget cũ
        for widget in self.class_frame.winfo_children():
            widget.destroy()

        # Xóa count labels cũ và entry widgets cũ
        self.count_labels.clear()
        self.entry_widgets.clear()

        # Lấy danh sách class mẹ (6 cụm chính)
        parent_indices = sorted(list(self.parent_classes.keys()))
        
        # Tạo 2 hàng: hàng trên và hàng dưới
        top_row_frame = ttk.Frame(self.class_frame)
        top_row_frame.pack(fill="x", pady=5)
        
        bottom_row_frame = ttk.Frame(self.class_frame)
        bottom_row_frame.pack(fill="x", pady=5)

        # Phân chia 6 cụm thành 2 hàng, mỗi hàng 3 cụm
        for i, parent_index in enumerate(parent_indices):
            if i < 6:  # Chỉ lấy 6 cụm đầu tiên
                parent_name = self.class_mapping[parent_index].get(lang, f"Parent_{parent_index}")
                
                # Chọn hàng (0-2: hàng trên, 3-5: hàng dưới)
                if i < 3:
                    row_frame = top_row_frame
                    col = i
                else:
                    row_frame = bottom_row_frame
                    col = i - 3
                
                # Tạo section cho class mẹ
                section_frame = ttk.LabelFrame(row_frame, text=parent_name, padding=5)
                section_frame.pack(side="left", fill="both", expand=True, padx=5)
                
                # Tìm tất cả class con thuộc class mẹ này
                child_indices = []
                for idx in self.class_indexes:
                    if idx > parent_index:
                        # Kiểm tra xem có phải class con không (dựa trên index liên tiếp)
                        if idx not in self.parent_classes:  # Không phải class mẹ
                            child_indices.append(idx)
                        else:
                            break  # Đã gặp class mẹ khác
                
                # Tạo các class con
                for child_index in child_indices:
                    class_name = self.class_mapping[child_index].get(lang, f"Class_{child_index}")
                    self.create_class_row(section_frame, class_name, child_index)

    def create_class_row(self, frame, class_name, class_index):
        count_var = self.counts_all[class_index]

        row = ttk.Frame(frame)
        row.pack(fill="x", pady=1)

        # Hiển thị tên class
        ttk.Label(row, text=class_name, width=22, anchor="w").pack(side="left")
        
        # Frame cho các nút điều khiển
        control_frame = ttk.Frame(row)
        control_frame.pack(side="right")
        
        ttk.Button(control_frame, text="-", width=2, 
                  command=lambda: self.decrement(class_index)).pack(side="left")
        
        # Tạo Entry widget cho nhập số trực tiếp
        entry = ttk.Entry(control_frame, width=4, justify="center", 
                         validate="key", validatecommand=self.vcmd)
        entry.pack(side="left", padx=2)
        
        # Bind sự kiện khi nhấn Enter
        entry.bind('<Return>', lambda e, idx=class_index: self.update_from_entry(idx))
        # Bind sự kiện khi focus out
        entry.bind('<FocusOut>', lambda e, idx=class_index: self.update_from_entry(idx))
        
        # Lưu entry widget
        self.entry_widgets[class_index] = entry
        
        # Tạo label và lưu vào count_labels
        count_label = ttk.Label(control_frame, textvariable=count_var, width=4, 
                              anchor="center", background="white", relief="solid")
        count_label.pack(side="left", padx=2)
        self.count_labels[class_index] = count_label
        
        ttk.Button(control_frame, text="+", width=2, 
                  command=lambda: self.increment(class_index)).pack(side="left")
        
        # Đồng bộ giá trị ban đầu
        self.sync_entry_value(class_index)

    def sync_entry_value(self, class_index):
        """Đồng bộ giá trị từ IntVar sang Entry"""
        if class_index in self.entry_widgets:
            self.entry_widgets[class_index].delete(0, tk.END)
            self.entry_widgets[class_index].insert(0, str(self.counts_all[class_index].get()))

    def update_from_entry(self, class_index):
        """Cập nhật giá trị từ Entry widget"""
        if class_index in self.entry_widgets:
            entry_value = self.entry_widgets[class_index].get()
            if entry_value.strip() == "":
                new_value = 0
            else:
                try:
                    new_value = int(entry_value)
                    if new_value < 0:
                        new_value = 0
                        self.entry_widgets[class_index].delete(0, tk.END)
                        self.entry_widgets[class_index].insert(0, "0")
                except ValueError:
                    new_value = self.counts_all[class_index].get()
                    self.entry_widgets[class_index].delete(0, tk.END)
                    self.entry_widgets[class_index].insert(0, str(new_value))
            
            self.counts_all[class_index].set(new_value)

    # ----------------------------
    # HÀM ĐIỀU KHIỂN ĐẾM
    # ----------------------------
    def increment(self, class_index):
        self.counts_all[class_index].set(self.counts_all[class_index].get() + 1)
        self.sync_entry_value(class_index)

    def decrement(self, class_index):
        val = self.counts_all[class_index].get()
        if val > 0:
            self.counts_all[class_index].set(val - 1)
            self.sync_entry_value(class_index)

    # ----------------------------
    # QUẢN LÝ THỜI GIAN
    # ----------------------------
    def start_timer(self):
        if self.is_paused:
            self.session_start = time.time()
            self.is_paused = False

    def pause_timer(self):
        if not self.is_paused and self.session_start:
            elapsed = time.time() - self.session_start
            self.total_work_time += elapsed
            self.is_paused = True
            self.session_start = None

    def get_total_elapsed_seconds(self):
        if self.is_paused or not self.session_start:
            return int(self.total_work_time)
        else:
            current_elapsed = time.time() - self.session_start
            return int(self.total_work_time + current_elapsed)

    def format_seconds_hms(self, seconds):
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h:02d}:{m:02d}:{s:02d}"

    def update_timer_display(self):
        total_seconds = self.get_total_elapsed_seconds()
        self.timer_label.config(text=f"Working Time: {self.format_seconds_hms(total_seconds)}")
        self.root.after(1000, self.update_timer_display)

    # ----------------------------
    # LƯU FILE EXCEL
    # ----------------------------
    def save_to_excel(self):
        dataset_name = self.dataset_name_entry.get().strip()
        if not dataset_name:
            messagebox.showerror("Error", "Please enter dataset name")
            return

        save_lang = tk.StringVar(value=self.current_language.get())
        save_window = tk.Toplevel(self.root)
        save_window.title("Select Save Language")

        ttk.Label(save_window, text="Select language to save:").pack(pady=10)
        lang_menu = ttk.OptionMenu(save_window, save_lang, self.current_language.get(), *self.languages)
        lang_menu.pack(pady=5)

        def confirm_save():
            self._save_to_excel_internal(dataset_name, save_lang.get())
            save_window.destroy()

        ttk.Button(save_window, text="Save", command=confirm_save).pack(pady=10)

    def _save_to_excel_internal(self, dataset_name, save_lang):
        filename = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")])
        if not filename:
            return

        elapsed_seconds = self.get_total_elapsed_seconds()
        elapsed_str = self.format_seconds_hms(elapsed_seconds)

        # CHỈ lấy class con (không bao gồm class mẹ)
        save_classes = []
        save_counts = []
        
        for index in self.child_classes:  # Chỉ lấy class con
            class_name = self.class_mapping[index].get(save_lang, f"Class_{index}")
            save_classes.append(class_name)
            save_counts.append(self.counts_all[index].get())

        if os.path.exists(filename):
            wb = openpyxl.load_workbook(filename)
            # Tìm sheet phù hợp hoặc tạo mới
            sheet_name = f"Counts_{save_lang}"
            if sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
            else:
                ws = wb.create_sheet(sheet_name)
        else:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = f"Counts_{save_lang}"

        # Tạo header
        if ws.max_row == 0 or [cell.value for cell in ws[1]][2:] != save_classes:
            ws.delete_rows(1, ws.max_row)
            ws.append(["Dataset Name", "Working Time"] + save_classes)

        # Ghi đè nếu dataset trùng
        found = False
        for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=False), start=2):
            if row[0].value == dataset_name:
                row[0].value = dataset_name
                row[1].value = elapsed_str
                for i, cell in enumerate(row[2:2+len(save_counts)], start=0):
                    if i < len(save_counts):
                        cell.value = save_counts[i]
                found = True
                break

        if not found:
            ws.append([dataset_name, elapsed_str] + save_counts)

        wb.save(filename)
        messagebox.showinfo("Success", f"Saved to {filename}")

    # ----------------------------
    # LOAD FILE EXCEL
    # ----------------------------
    def load_from_excel(self):
        filename = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx")])
        if not filename:
            return

        dataset_name = self.dataset_name_entry.get().strip()
        if not dataset_name:
            messagebox.showerror("Error", "Please enter dataset name before loading")
            return

        try:
            wb = openpyxl.load_workbook(filename)
            
            # Tìm sheet phù hợp
            ws = None
            loaded_lang = None
            for sheet_name in wb.sheetnames:
                sheet = wb[sheet_name]
                header = [cell.value for cell in sheet[1]] if sheet.max_row > 0 else []
                if len(header) >= 3:
                    excel_classes = header[2:]
                    # Kiểm tra xem header có khớp với bất kỳ ngôn ngữ nào không
                    for lang in self.languages:
                        # CHỈ so sánh class con
                        lang_child_classes = []
                        for index in self.child_classes:
                            class_name = self.class_mapping[index].get(lang, f"Class_{index}")
                            lang_child_classes.append(class_name)
                        
                        if excel_classes == lang_child_classes:
                            ws = sheet
                            loaded_lang = lang
                            break
                if ws:
                    break
            
            if not ws:
                ws = wb.active

            found = False
            for row in ws.iter_rows(min_row=2, values_only=True):
                if row and row[0] == dataset_name:
                    # Load thời gian làm việc
                    time_str = str(row[1])
                    if ':' in time_str:
                        h, m, s = map(int, time_str.split(":"))
                        self.total_work_time = h*3600 + m*60 + s
                    self.session_start = None
                    self.is_paused = True

                    # Load số lượng - ánh xạ theo class index
                    header = [cell.value for cell in ws[1]]
                    excel_classes = header[2:]
                    
                    # Reset tất cả counts về 0 trước
                    for index in self.class_indexes:
                        self.counts_all[index].set(0)
                    
                    # Ánh xạ class từ Excel vào class index (CHỈ class con)
                    for i, excel_class in enumerate(excel_classes):
                        if i + 2 < len(row) and row[i + 2] is not None:
                            # Tìm class index tương ứng (CHỈ trong class con)
                            for index in self.child_classes:
                                lang_dict = self.class_mapping[index]
                                if excel_class in lang_dict.values():
                                    self.counts_all[index].set(row[i + 2])
                                    # Đồng bộ giá trị với entry widget
                                    if index in self.entry_widgets:
                                        self.sync_entry_value(index)
                                    break

                    found = True
                    # Cập nhật ngôn ngữ hiển thị nếu tìm thấy ngôn ngữ phù hợp
                    if loaded_lang:
                        self.current_language.set(loaded_lang)
                        self.update_language(loaded_lang)
                    
                    messagebox.showinfo("Success", f"Loaded dataset '{dataset_name}' from {filename}")
                    break

            if not found:
                messagebox.showinfo("Info", f"Dataset '{dataset_name}' not found in {filename}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file: {e}")

# ==========================
# CHẠY CHƯƠNG TRÌNH
# ==========================
if __name__ == "__main__":
    root = tk.Tk()
    app = CounterApp(root)
    root.mainloop()