import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json, random
import logging
logging.basicConfig(
    level=logging.INFO,
    filename='lottery.log',
    filemode='a',
    encoding='utf-8',
    format='%(asctime)s - %(levelname)s - %(message)s',
)

from award import Award

class LotteryApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("转盘")
        self.geometry("600x600")
        self.load_config()
        self.create_awards()
        self.validate_total_prob()
        self.update_probabilities()
        self.create_widgets()
        self.update_awards_display()
        self.attributes('-alpha', self.opacity)

    def load_config(self, config_file='config.json'):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
        except FileNotFoundError:
            messagebox.showerror("错误", f"配置文件 {config_file} 未找到")
            self.destroy()
            return
        try:
            self.opacity = cfg.get('opacity', 1)
            self.records = cfg['records']
            self.award_cfgs = cfg['awards']
        except KeyError as e:
            messagebox.showerror("错误", f"配置文件格式错误: {e}")
            self.destroy()
            return

    def save_config(self, config_file='config.json'):
        cfg = {
            'opacity': self.opacity,
            'records': self.records,
            'awards': [
                award.to_json() for award in self.awards
            ]
        }
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, ensure_ascii=False, indent=4)

    def create_awards(self):
        try:
            self.awards = [
                Award(c['name'], c['award_type'], c['base_prob'], c.get('remaining'), c.get('operation'))
                for c in self.award_cfgs
            ]
        except ValueError as e:
            messagebox.showerror("错误", f"奖项配置错误: {e}")
            self.destroy()
            return

    def validate_total_prob(self):
        total = sum(a.base_prob for a in self.awards)
        if total != 100:
            messagebox.showerror("错误", f"概率总和必须为100%（当前：{total}%）")
            self.destroy()

    def update_probabilities(self):
        active = [a for a in self.awards if a.is_active()]
        total = sum(a.base_prob for a in active)
        for a in self.awards:
            a.current_prob = (a.base_prob / total * 100) if a.is_active() else 0

    def create_widgets(self):
        """创建UI组件"""
        # 主布局框架
        main_frame = ttk.Frame(self)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # 左半边：奖项和概率
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side='left', fill='both', expand=True, padx=5, pady=5)

        # 右半边：抽奖按钮和结果显示
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side='right', fill='both', padx=5, pady=5)
        
        # 底部：项目状态
        bottom_frame = ttk.Frame(self)
        bottom_frame.pack(side='bottom', fill='x', padx=10, pady=10)
        
        # ===== 左半边内容 =====
        awards_frame = ttk.LabelFrame(left_frame, text="奖项设置")
        awards_frame.pack(fill='both', expand=True)
        
        # 表头
        headers = ["奖项名称", "基础概率", "当前概率", "剩余数量"]
        for col, text in enumerate(headers):
            ttk.Label(awards_frame, text=text).grid(row=0, column=col, padx=5, pady=2)
        
        # 奖项行
        self.award_rows = []
        for i, award in enumerate(self.awards):
            row = []
            row.append(ttk.Label(awards_frame, text=award.name))
            # row.append(ttk.Label(awards_frame, text=award.award_type))
            row.append(ttk.Label(awards_frame, text=f"{award.base_prob}%"))
            row.append(ttk.Label(awards_frame, text=f"{award.current_prob:.2f}%"))
            
            if award.award_type == '限量':
                spin = ttk.Spinbox(awards_frame, from_=0, to=999, width=5)
                spin.set(award.remaining)
                spin.configure(
                    command=lambda a=award, s=spin: self.update_quantity(a, s.get()),
                )
                spin.bind('<FocusOut>', lambda e, a=award, s=spin: self.update_quantity(a, s.get()))
                spin.bind('<Return>', lambda e, a=award, s=spin: self.update_quantity(a, s.get()))
                row.append(spin)
            else:
                row.append(ttk.Label(awards_frame, text="N/A"))
            
            for col, widget in enumerate(row):
                widget.grid(row=i+1, column=col, padx=5, pady=2)
            self.award_rows.append(row)
        
        # ===== 右半边内容 =====
        control_frame = ttk.LabelFrame(right_frame, text="抽奖控制")
        control_frame.pack(fill='both', expand=True)
        
        # 抽奖按钮
        ttk.Button(control_frame, text="单抽", command=lambda: self.draw(1)).pack(pady=5, fill='x')
        ttk.Button(control_frame, text="十连抽", command=lambda: self.draw(10)).pack(pady=5, fill='x')
        
        # 自定义抽奖
        custom_frame = ttk.Frame(control_frame)
        custom_frame.pack(pady=5, fill='x')
        self.custom_entry = ttk.Entry(custom_frame, width=5)
        self.custom_entry.pack(side='left', pady=5)
        ttk.Button(custom_frame, text="自定义抽", command=self.custom_draw).pack(pady=5, fill='x')
        
        # 结果显示
        result_frame = ttk.LabelFrame(right_frame, text="抽奖结果")
        result_frame.pack(fill='both', expand=True, pady=5)
        self.result_text = tk.Text(result_frame, height=10)
        self.result_text.config(state='disabled')
        self.result_text.pack(fill='both', expand=True, padx=5, pady=5)
        
        # ===== 底部内容 =====
        status_frame = ttk.LabelFrame(bottom_frame, text="当前状态")
        status_frame.pack(fill='x', pady=5)
        
        # 创建样式对象
        style = ttk.Style()

        # 定义自定义样式
        style.configure("Custom.TLabel", font=("SimHei", 20))

        self.record_labels = {}
        for record_key, record_value in self.records.items():
            label = ttk.Label(status_frame, text=f"{record_key}: {record_value}", style="Custom.TLabel")
            label.pack(side='left', padx=5)
            self.record_labels[record_key] = label

    def update_quantity(self, award, quantity):
        """更新实体礼物数量"""
        try:
            quantity = int(quantity)
            award.remaining = quantity
            self.update_probabilities()
            self.update_awards_display()
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")
        self.save_config()

    def update_awards_display(self):
        """更新界面显示"""
        for i, award in enumerate(self.awards):
            self.award_rows[i][2].config(text=f"{award.current_prob:.2f}%")
            if award.award_type == '限量':
                self.award_rows[i][-1].set(award.remaining)

    def apply_effect(self, award):
        """应用效果到项目"""
        if award.award_type in self.records:
            value_before = self.records[award.award_type]
            self.records[award.award_type] = award.effect(self.records[award.award_type])
            if self.records[award.award_type] < 0:
                self.records[award.award_type] = 0
            value_after = self.records[award.award_type]
            logging.info(f"抽奖结果: {award.name} ({award.award_type}): {value_before} -> {value_after}")
        elif award.award_type == '限量':
            value_before = award.remaining
            award.remaining -= 1
            value_after = award.remaining
            logging.info(f"抽奖结果: {award.name} ({award.award_type}): {value_before} -> {value_after}")
        elif award.award_type == '其他':
            logging.info(f"抽奖结果: {award.name}")

    def draw(self, times):
        """执行抽奖"""
        logging.info(f"抽奖次数: {times}")

        results = {}
        for _ in range(times):
            # 创建概率轮盘
            active_awards = [a for a in self.awards if a.is_active()]
            if not active_awards:
                messagebox.showinfo("提示", "没有可用奖项")
                return
                
            selected = random.choices(active_awards, weights=[a.base_prob for a in active_awards], k=1)[0]
            
            # 处理抽奖结果
            self.apply_effect(selected)
            results[selected.name] = results.get(selected.name, 0) + 1

        # 保存剩余数量到配置文件
        self.save_config()

        # 更新状态标签
        for record_key, record_value in self.records.items():
            self.record_labels[record_key].config(text=f"{record_key}: {record_value}")

        # 更新当前概率
        self.update_probabilities()

        # 显示结果
        self.result_text.config(state='normal')
        self.result_text.delete(1.0, tk.END)
        for name, count in results.items():
            self.result_text.insert(tk.END, f"{name}: {count}次\n")
        self.result_text.config(state='disabled')
        
        self.update_awards_display()

    def custom_draw(self):
        """自定义抽奖次数"""
        try:
            times = int(self.custom_entry.get())
            if times > 0:
                self.draw(times)
        except ValueError:
            messagebox.showerror("错误", "请输入有效数字")

if __name__ == '__main__':
    LotteryApp().mainloop()