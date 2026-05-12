import json
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
import re
from datetime import datetime


class DeepSeekSearchTool:
    def __init__(self, root):
        self.root = root
        self.root.title("DeepSeek 对话搜索工具")
        self.root.geometry("1200x700")

        # 存储数据
        self.all_messages = []  # 存储所有消息
        self.current_results = []  # 存储当前搜索结果

        # 创建界面
        self.setup_ui()

    def setup_ui(self):
        """创建用户界面"""

        # 顶部框架 - 文件选择
        top_frame = tk.Frame(self.root)
        top_frame.pack(pady=10, padx=10, fill=tk.X)

        tk.Button(top_frame, text="📁 选择JSON文件", command=self.load_json_file,
                  bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), padx=20).pack(side=tk.LEFT, padx=5)

        tk.Button(top_frame, text="📂 选择文件夹（批量导入）", command=self.load_folder,
                  bg="#2196F3", fg="white", font=("Arial", 10, "bold"), padx=20).pack(side=tk.LEFT, padx=5)

        self.file_label = tk.Label(top_frame, text="未加载文件", fg="gray")
        self.file_label.pack(side=tk.LEFT, padx=20)

        # 统计信息
        self.stats_label = tk.Label(top_frame, text="", fg="blue")
        self.stats_label.pack(side=tk.RIGHT, padx=10)

        # 搜索框架
        search_frame = tk.Frame(self.root)
        search_frame.pack(pady=10, padx=10, fill=tk.X)

        tk.Label(search_frame, text="🔍 搜索关键词：", font=("Arial", 11)).pack(side=tk.LEFT)

        self.search_entry = tk.Entry(search_frame, font=("Arial", 11), width=40)
        self.search_entry.pack(side=tk.LEFT, padx=10)
        self.search_entry.bind("<Return>", lambda e: self.search_messages())

        # 搜索选项
        self.case_sensitive = tk.BooleanVar()
        tk.Checkbutton(search_frame, text="区分大小写", variable=self.case_sensitive).pack(side=tk.LEFT, padx=10)

        self.search_in_content = tk.BooleanVar(value=True)
        tk.Checkbutton(search_frame, text="搜索消息内容", variable=self.search_in_content).pack(side=tk.LEFT, padx=5)

        self.search_in_role = tk.BooleanVar()
        tk.Checkbutton(search_frame, text="搜索角色(我/AI)", variable=self.search_in_role).pack(side=tk.LEFT, padx=5)

        tk.Button(search_frame, text="搜索", command=self.search_messages,
                  bg="#FF9800", fg="white", font=("Arial", 10, "bold"), padx=20).pack(side=tk.LEFT, padx=20)

        tk.Button(search_frame, text="清空结果", command=self.clear_results,
                  bg="#9E9E9E", fg="white", padx=15).pack(side=tk.LEFT)

        # 主内容区域（左右分栏）
        main_paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 左侧：搜索结果列表
        left_frame = tk.Frame(main_paned)
        main_paned.add(left_frame, width=400)

        tk.Label(left_frame, text="搜索结果", font=("Arial", 12, "bold")).pack(pady=5)

        # 结果列表
        self.result_listbox = tk.Listbox(left_frame, font=("Arial", 10), selectmode=tk.SINGLE)
        self.result_listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        self.result_listbox.bind('<<ListboxSelect>>', self.on_result_select)

        # 添加滚动条
        scrollbar = tk.Scrollbar(self.result_listbox)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.result_listbox.yview)

        # 右侧：消息详情
        right_frame = tk.Frame(main_paned)
        main_paned.add(right_frame, width=800)

        tk.Label(right_frame, text="消息详情", font=("Arial", 12, "bold")).pack(pady=5)

        # 消息内容显示区
        self.message_text = ScrolledText(right_frame, wrap=tk.WORD, font=("Consolas", 11))
        self.message_text.pack(fill=tk.BOTH, expand=True, pady=5)

        # 底部的状态栏
        self.status_bar = tk.Label(self.root, text="就绪", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def load_json_file(self):
        """加载单个JSON文件"""
        file_path = filedialog.askopenfilename(
            title="选择DeepSeek导出的JSON文件",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if file_path:
            self.load_data(file_path)

    def load_folder(self):
        """批量加载文件夹中的所有JSON文件"""
        folder_path = filedialog.askdirectory(title="选择包含JSON文件的文件夹")

        if folder_path:
            json_files = [f for f in os.listdir(folder_path) if f.endswith('.json')]

            if not json_files:
                messagebox.showwarning("警告", "文件夹中没有找到JSON文件！")
                return

            all_data = []
            for file in json_files:
                file_path = os.path.join(folder_path, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        all_data.append({
                            'file': file,
                            'data': data
                        })
                except Exception as e:
                    print(f"读取 {file} 失败: {e}")

            self.process_multiple_files(all_data)
            self.file_label.config(text=f"已加载 {len(all_data)} 个对话文件")

    def process_multiple_files(self, files_data):
        """处理多个JSON文件"""
        self.all_messages = []

        for file_info in files_data:
            data = file_info['data']
            file_name = file_info['file']
            self.parse_json_data(data, file_name)

        self.update_stats()
        self.status_bar.config(text=f"成功加载 {len(files_data)} 个文件，共 {len(self.all_messages)} 条消息")
        messagebox.showinfo("成功", f"已加载 {len(files_data)} 个对话文件\n共 {len(self.all_messages)} 条消息")

    def load_data(self, file_path):
        """加载单个JSON文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.all_messages = []
            self.parse_json_data(data, os.path.basename(file_path))

            self.update_stats()
            self.file_label.config(text=f"已加载: {os.path.basename(file_path)}")
            self.status_bar.config(text=f"加载成功！共 {len(self.all_messages)} 条消息")
            messagebox.showinfo("成功", f"已加载 {len(self.all_messages)} 条消息")

        except Exception as e:
            messagebox.showerror("错误", f"加载文件失败：{str(e)}")
            self.status_bar.config(text="加载失败")

    def parse_json_data(self, data, file_name=""):
        """解析JSON数据，提取所有消息"""
        # 判断JSON结构
        if isinstance(data, list):
            # 如果是列表形式
            for idx, item in enumerate(data):
                self.extract_messages(item, file_name, idx)
        elif isinstance(data, dict):
            # 如果是字典形式
            self.extract_messages(data, file_name, 0)
        else:
            print("未知的数据格式")

    def extract_messages(self, data, file_name, dialog_id):
        """提取消息"""
        # 处理不同的JSON结构
        if 'messages' in data:
            messages = data['messages']
            for msg_idx, msg in enumerate(messages):
                self.add_message(msg, file_name, dialog_id, msg_idx)
        elif 'chat_history' in data:
            messages = data['chat_history']
            for msg_idx, msg in enumerate(messages):
                self.add_message(msg, file_name, dialog_id, msg_idx)
        elif 'content' in data and 'role' in data:
            # 单条消息
            self.add_message(data, file_name, dialog_id, 0)

    def add_message(self, msg, file_name, dialog_id, msg_idx):
        """添加一条消息到列表"""
        role = msg.get('role', msg.get('author', 'unknown'))
        content = msg.get('content', msg.get('text', ''))
        timestamp = msg.get('timestamp', msg.get('created_at', ''))

        # 转换角色名
        if role == 'user' or role == '我':
            role_display = '👤 我'
        elif role == 'assistant' or role == 'DeepSeek':
            role_display = '🤖 DeepSeek'
        else:
            role_display = role

        self.all_messages.append({
            'dialog_id': dialog_id,
            'message_id': msg_idx,
            'file': file_name,
            'role': role_display,
            'role_raw': role,
            'content': content,
            'timestamp': timestamp,
            'preview': content[:100] + ('...' if len(content) > 100 else '')
        })

    def update_stats(self):
        """更新统计信息"""
        total_msgs = len(self.all_messages)

        # 统计对话数量
        unique_dialogs = set()
        for msg in self.all_messages:
            unique_dialogs.add(f"{msg['file']}_{msg['dialog_id']}")

        self.stats_label.config(text=f"📊 {len(unique_dialogs)} 个对话 | 💬 {total_msgs} 条消息")

    def search_messages(self):
        """搜索消息"""
        keyword = self.search_entry.get().strip()

        if not keyword:
            messagebox.showwarning("警告", "请输入搜索关键词！")
            return

        if not self.all_messages:
            messagebox.showwarning("警告", "请先加载JSON文件！")
            return

        # 清空之前的结果
        self.result_listbox.delete(0, tk.END)
        self.current_results = []

        # 搜索
        search_term = keyword if self.case_sensitive.get() else keyword.lower()

        for msg in self.all_messages:
            matches = False

            # 搜索内容
            if self.search_in_content.get():
                content = msg['content'] if self.case_sensitive.get() else msg['content'].lower()
                if search_term in content:
                    matches = True

            # 搜索角色
            if not matches and self.search_in_role.get():
                role = msg['role'] if self.case_sensitive.get() else msg['role'].lower()
                if search_term in role:
                    matches = True

            if matches:
                self.current_results.append(msg)
                # 在列表框中显示预览
                display_text = f"[{msg['file']}] {msg['role']}: {msg['preview']}"
                self.result_listbox.insert(tk.END, display_text)

        # 更新状态
        result_count = len(self.current_results)
        self.status_bar.config(text=f"找到 {result_count} 条包含 '{keyword}' 的消息")

        if result_count == 0:
            messagebox.showinfo("提示", f"未找到包含 '{keyword}' 的消息")

    def on_result_select(self, event):
        """当选择搜索结果时显示完整消息"""
        selection = self.result_listbox.curselection()
        if not selection:
            return

        index = selection[0]
        if index < len(self.current_results):
            msg = self.current_results[index]
            self.show_message_detail(msg)

    def show_message_detail(self, msg):
        """显示消息详情"""
        self.message_text.delete(1.0, tk.END)

        # 格式化显示
        detail = f"""
╔══════════════════════════════════════════════════════════════╗
║  消息详情
╠══════════════════════════════════════════════════════════════╣
║  📁 对话文件: {msg['file']}
║  🆔 对话ID: {msg['dialog_id']}  |  消息ID: {msg['message_id']}
║  👤 角色: {msg['role']}
"""

        if msg['timestamp']:
            detail += f"  ⏰ 时间戳: {msg['timestamp']}\n"

        detail += f"""
╠══════════════════════════════════════════════════════════════╣
║  📝 消息内容:
╠══════════════════════════════════════════════════════════════╣
{msg['content']}
╚══════════════════════════════════════════════════════════════╝
"""

        self.message_text.insert(1.0, detail)

        # 高亮关键词
        keyword = self.search_entry.get().strip()
        if keyword:
            self.highlight_text(keyword)

    def highlight_text(self, keyword):
        """高亮文本中的关键词"""
        start_pos = "1.0"
        while True:
            start_pos = self.message_text.search(keyword, start_pos, tk.END,
                                                 nocase=not self.case_sensitive.get())
            if not start_pos:
                break
            end_pos = f"{start_pos}+{len(keyword)}c"
            self.message_text.tag_add("highlight", start_pos, end_pos)
            start_pos = end_pos

        self.message_text.tag_config("highlight", background="yellow", foreground="black")

    def clear_results(self):
        """清空搜索结果"""
        self.result_listbox.delete(0, tk.END)
        self.message_text.delete(1.0, tk.END)
        self.current_results = []
        self.status_bar.config(text="已清空搜索结果")
        self.search_entry.delete(0, tk.END)


if __name__ == "__main__":
    root = tk.Tk()
    app = DeepSeekSearchTool(root)
    root.mainloop()