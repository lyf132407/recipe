import tkinter as tk
from tkinter import scrolledtext
from agent.react_agent import RecipeReActAgent

class CookAgentGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("联网智能做饭Agent")
        self.sessions = []
        self.current_session_index = 0
        self.session_counter = 0

        left_frame = tk.Frame(root, width=260)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        mid_frame = tk.Frame(root)
        mid_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        tk.Label(left_frame, text="会话列表", font=("黑体", 12, "bold")).pack(anchor=tk.W)
        listbox_frame = tk.Frame(left_frame)
        listbox_frame.pack(fill=tk.BOTH, expand=True)
        self.session_listbox = tk.Listbox(listbox_frame, width=28, activestyle="dotbox")
        self.session_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.session_listbox.bind("<<ListboxSelect>>", self.on_session_select)
        self.session_listbox.bind("<Button-3>", self.show_session_menu)

        scrollbar = tk.Scrollbar(listbox_frame, command=self.session_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.session_listbox.config(yscrollcommand=scrollbar.set)

        tk.Button(left_frame, text="新建对话", command=self.new_session).pack(fill=tk.X, pady=5)

        self.session_menu = tk.Menu(self.root, tearoff=0)
        self.session_menu.add_command(label="新建对话", command=self.new_session)
        self.session_menu.add_command(label="删除对话", command=self.delete_current_session)

        self.chat_box = scrolledtext.ScrolledText(mid_frame, height=22)
        self.chat_box.pack(fill=tk.BOTH, expand=True)
        self.chat_box.config(state=tk.DISABLED)

        entry_frame = tk.Frame(mid_frame)
        entry_frame.pack(fill=tk.X, pady=4)
        self.input_entry = tk.Entry(entry_frame, font=("宋体", 11))
        self.input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.input_entry.bind("<Return>", self.send_msg)
        tk.Button(entry_frame, text="发送", width=10, command=self.send_msg).pack(side=tk.RIGHT, padx=4)

        self.new_session()

    def new_session(self):
        self.session_counter += 1
        title = f"对话{self.session_counter}"
        session_id = f"session_{self.session_counter}"
        session = {
            "title": title,
            "session_id": session_id,
            "agent": RecipeReActAgent(session_id=session_id),
            "messages": []
        }
        self.sessions.append(session)
        self.current_session_index = len(self.sessions) - 1
        self.refresh_session_list()
        self.set_current_session(self.current_session_index)

    def refresh_session_list(self):
        self.session_listbox.delete(0, tk.END)
        for idx, session in enumerate(self.sessions):
            prefix = "▶ " if idx == self.current_session_index else "   "
            self.session_listbox.insert(tk.END, f"{prefix}{session['title']}")
        self.session_listbox.selection_clear(0, tk.END)
        self.session_listbox.selection_set(self.current_session_index)
        self.session_listbox.activate(self.current_session_index)

    def set_current_session(self, index):
        if index < 0 or index >= len(self.sessions):
            return
        self.current_session_index = index
        self.refresh_session_list()
        self.load_current_session_history()

    def delete_current_session(self):
        if len(self.sessions) <= 1:
            return
        del self.sessions[self.current_session_index]
        if self.current_session_index >= len(self.sessions):
            self.current_session_index = len(self.sessions) - 1
        self.refresh_session_list()
        self.load_current_session_history()

    def on_session_select(self, event=None):
        selection = self.session_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        self.set_current_session(index)

    def show_session_menu(self, event):
        try:
            index = self.session_listbox.nearest(event.y)
            self.session_listbox.selection_clear(0, tk.END)
            self.session_listbox.selection_set(index)
            self.set_current_session(index)
        except Exception:
            pass
        self.session_menu.tk_popup(event.x_root, event.y_root)

    def load_current_session_history(self):
        self.chat_box.config(state=tk.NORMAL)
        self.chat_box.delete(1.0, tk.END)
        session = self.sessions[self.current_session_index]
        for role, text in session["messages"]:
            self.chat_box.insert(tk.END, f"【{role}】：{text}\n")
        self.chat_box.see(tk.END)
        self.chat_box.config(state=tk.DISABLED)

    def append_message(self, role, text):
        session = self.sessions[self.current_session_index]
        session["messages"].append((role, text))
        self.chat_box.config(state=tk.NORMAL)
        self.chat_box.insert(tk.END, f"【{role}】：{text}\n")
        self.chat_box.see(tk.END)
        self.chat_box.config(state=tk.DISABLED)

    def send_msg(self, event=None):
        user_text = self.input_entry.get().strip()
        if not user_text:
            return
        self.input_entry.delete(0, tk.END)
        self.append_message("我", user_text)
        agent = self.sessions[self.current_session_index]["agent"]
        reply = agent.react_thought_action(user_text)
        self.append_message("助手", reply)


if __name__ == "__main__":
    win = tk.Tk()
    app = CookAgentGUI(win)
    win.mainloop()
