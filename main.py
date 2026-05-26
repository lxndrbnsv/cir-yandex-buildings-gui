# TODO: Телемаркетинг -> Закрыто и не реализовано

import warnings
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.proxy import Proxy, ProxyType

from services.queries import ReadQueries
from services.parse import GetCompanies, GetCompanyData
from services.write import WriteXLSX
from services.util import ClearWB, parse_query_string
from services.proxy import GetProxy, AddProxy


warnings.filterwarnings("ignore", category=UserWarning)


def create_browser():
    svc = Service()
    opts = webdriver.ChromeOptions()
    # opts.add_argument("--headless")
    return webdriver.Chrome(service=svc, options=opts)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Yandex Maps scraper")
        self.resizable(False, False)
        self.browser = create_browser()
        self._build_ui()

    def _build_ui(self):
        # File path row
        file_frame = ttk.Frame(self)
        file_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(file_frame, text="Путь к файлу с адресами:").pack(side=tk.LEFT)
        self.file_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.file_var, width=50).pack(side=tk.LEFT, padx=5)
        ttk.Button(file_frame, text="Обзор", command=self._browse_file).pack(side=tk.LEFT)

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10, pady=2)

        # Proxy row
        proxy_frame = ttk.Frame(self)
        proxy_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(proxy_frame, text="Добавить прокси (ip:port):").pack(side=tk.LEFT)
        self.proxy_var = tk.StringVar()
        ttk.Entry(proxy_frame, textvariable=self.proxy_var, width=25).pack(side=tk.LEFT, padx=5)
        ttk.Button(proxy_frame, text="Добавить прокси", command=self._add_proxy).pack(side=tk.LEFT)

        # Action row
        action_frame = ttk.Frame(self)
        action_frame.pack(fill=tk.X, padx=10, pady=5)
        self.start_btn = ttk.Button(action_frame, text="Запуск", command=self._start)
        self.start_btn.pack(side=tk.LEFT)
        self.use_proxy_var = tk.BooleanVar()
        ttk.Checkbutton(
            action_frame, text="Использовать прокси", variable=self.use_proxy_var
        ).pack(side=tk.LEFT, padx=10)
        ttk.Separator(action_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Button(
            action_frame, text="Очистить файл результатов", command=self._clear_results
        ).pack(side=tk.LEFT)
        ttk.Separator(action_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Button(action_frame, text="Выход", command=self._quit).pack(side=tk.LEFT)

        # Log output
        log_frame = ttk.Frame(self)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.log_text = tk.Text(log_frame, height=15, width=80, state=tk.DISABLED)
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _log(self, message):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, str(message) + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _browse_file(self):
        path = filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if path:
            self.file_var.set(path)

    def _add_proxy(self):
        proxy = self.proxy_var.get().strip()
        if ":" not in proxy:
            messagebox.showerror("Ошибка", "Неправильный формат прокси!")
        else:
            AddProxy(proxy)
            self.proxy_var.set("")
            messagebox.showinfo("Успех", "Прокси добавлен!")

    def _clear_results(self):
        ClearWB()
        messagebox.showinfo("Успех", "Файл результатов очищен!")

    def _start(self):
        filepath = self.file_var.get()
        if not filepath:
            messagebox.showwarning("Внимание", "Добавьте файл с адресами!")
            return
        self.start_btn.configure(state=tk.DISABLED)
        threading.Thread(target=self._run_scraping, args=(filepath,), daemon=True).start()

    def _run_scraping(self, filepath):
        proxy = None
        if self.use_proxy_var.get():
            proxy_ip = GetProxy().proxy_addr
            if proxy_ip is None:
                self._log(
                    "Отсутствует файл с прокси либо формат прокси неверный!\n"
                    "Парсер будет запущен без использования прокси."
                )
            else:
                proxy = Proxy()
                proxy.proxy_type = ProxyType.MANUAL
                proxy.ssl_proxy = proxy_ip
                capabilities = webdriver.DesiredCapabilities.CHROME
                proxy.add_to_capabilities(capabilities)

        queries = ReadQueries(filepath=filepath).queries

        for q in queries:
            for attempt in range(2):
                try:
                    self._log(q)
                    companies = GetCompanies(browser=self.browser, query=q).results

                    self._log(f"Собрано {len(companies)} организаций.")
                    self._log("Обработка данных:")
                    for company in companies:
                        company_dict = GetCompanyData(
                            browser=self.browser, company_link=company
                        ).data
                        if company_dict is not None:
                            company_dict["address"] = q
                            company_dict["building_id"] = parse_query_string(q)
                            WriteXLSX(company_dict=company_dict)
                            self._log("Данные записаны")
                        else:
                            self._log("Отсутствуют контактные данные!")
                    break
                except Exception as e:
                    self._log(f"Ошибка: {e}")
                    if attempt == 0:
                        self._log("Перезапуск браузера...")
                        try:
                            self.browser.quit()
                        except Exception:
                            pass
                        self.browser = create_browser()
                    else:
                        self._log(f"Пропускаем: {q}")
            self._log("--- --- ---")

        self.after(0, lambda: self.start_btn.configure(state=tk.NORMAL))
        self.after(0, lambda: messagebox.showinfo("Готово", "Сбор данных завершён!"))

    def _quit(self):
        try:
            self.browser.quit()
        except Exception:
            pass
        self.destroy()


if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app._quit)
    app.mainloop()
