#!/usr/bin/env python
# coding: utf-8

import os, sys, time, logging
import re, csv, requests, ctypes
from threading import Thread, Lock
from datetime import datetime
from apscheduler.schedulers.qt import QtScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from PyQt5.QtGui import QIcon
from PyQt5 import QtGui, uic
from PyQt5.QtCore import Qt, QObject, pyqtSignal, QPropertyAnimation
from PyQt5.QtWidgets import QApplication, QTableWidgetItem, QHeaderView, QMessageBox


class StatsSpider():
    def __init__(self):
        self.url_dict = {
            "cryptoBubbles": "https://cryptobubbles.net/backend/data/bubbles1000.usd.json",
            "tokenInsight": "https://cn.tokeninsight.com/zh/coins/{}/overview"
        }

    def get_html(self, url):
        headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36",
            "accept-language": "zh-CN,zh;q=0.9"
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.text
        except Exception:
            print("Can't get info from cryptobubbles.net!")
            pass

    def data_parser(self, data):
        try:
            data_list = re.findall(r"(\{\"id\":.*?\}\}),", data)

            parsed_data = []
            for item in data_list:
                if re.search(r'{"binance":null', item):
                    pass
                else:
                    crypto_name = re.search(r"\"name\":\"(.*?)\",", item).group(1)
                    rank = re.search(r"\"rank\":(.*?),", item).group(1)
                    symbol = re.search(r"\"symbol\":\"(.*?)\",", item).group(1)
                    price = re.search(r"\"price\":(.*?),", item).group(1)
                    volume = re.search(r"\"volume\":(.*?),", item).group(1)
                    market_cap = re.search(r"\"marketcap\":(.*?),", item).group(1)
                    hour_pfm = re.search(r"\"hour\":(.*?),", item).group(1)
                    day_pfm = re.search(r"\"day\":(.*?),", item).group(1)
                    #week_pfm = re.search(r"\"week\":(.*?),", item).group(1)
                    #month_pfm = re.search(r"\"month\":(.*?),", item).group(1)
                    #year_pfm = re.search(r"\"year\":(.*?),", item).group(1)
                    #min15_pfm = re.search(r"\"min15\":(.*?),", item).group(1)
                    vm_rate = float(volume) / float(market_cap)

                    if market_cap.find(".") > -1:
                        market_cap, decimal = market_cap.split(".")
                    parsed_data.append(
                        (crypto_name, rank, symbol, float(price), int(volume), int(market_cap),
                         float(hour_pfm) / 100, float(day_pfm) / 100, vm_rate
                         )
                    )
            return parsed_data
        except Exception as e:
            print("data_parser error: {}".format(e))

    def data_sorter(self, parsed_data, data_range=20):
        hour_pfm_asc = (sorted(parsed_data, key=lambda x: x[6]))[0:data_range]
        hour_pfm_desc = (sorted(parsed_data, key=lambda x: x[6], reverse=True))[0:data_range]
        day_pfm_asc = (sorted(parsed_data, key=lambda x: x[7]))[0:data_range]
        day_pfm_desc = (sorted(parsed_data, key=lambda x: x[7], reverse=True))[0:data_range]

        return [hour_pfm_asc, hour_pfm_desc, day_pfm_asc, day_pfm_desc]

    def txt_writer(self, content, datetime):
        if os.path.exists(".\\crypto_records\\"):
            pass
        else:
            os.mkdir(".\\crypto_records\\")

        try:
            with open(".\\crypto_records\\{} rank of cryptos.txt".format(datetime), "a") as txtfile:
                txtfile.write(content)
        except IOError:
            pass

    def gen_txt_file(self, parsed_data):
        titles = ["排行", "名称", "简写", "价格", "市值", "交易量", "时涨跌幅", "日涨跌幅", "交易量/市值"]
        now = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
        dt = datetime.now().strftime("%Y-%m-%d  %H%M%S")
        self.txt_writer("[{:<}   GMT+8]\n\n".format(now), dt)

        for lst in parsed_data:
            self.txt_writer("=" * 156 + "\n\n", dt)
            self.txt_writer("{0:<12s}".format(titles[0]), dt)
            self.txt_writer("{0:<32s}".format(titles[1]), dt)
            self.txt_writer("{0:^12s}".format(titles[2]), dt)
            self.txt_writer("{0:^13s}".format(titles[3]), dt)
            self.txt_writer("{0:^19s}".format(titles[4]), dt)
            self.txt_writer("{0:^18s}".format(titles[5]), dt)
            self.txt_writer("{0:<10s}".format(titles[6]), dt)
            self.txt_writer("{0:<8s}".format(titles[7]), dt)
            self.txt_writer("{0:<s}\n\n".format(titles[8]), dt)
            for crypto in lst:
                self.txt_writer("{0:<12s}".format(crypto[1]), dt)
                self.txt_writer("{0:<40s}".format(crypto[0]), dt)
                self.txt_writer("{0:<12s}".format(crypto[2]), dt)
                self.txt_writer("{0:>12f}".format(crypto[3]), dt)
                self.txt_writer("{0:>20,d}".format(crypto[5]), dt)
                self.txt_writer("{0:>20,d}".format(crypto[4]), dt)
                self.txt_writer("{0:>12.2%}".format(crypto[6]), dt)
                self.txt_writer("{0:>12.2%}".format(crypto[7]), dt)
                self.txt_writer("{0:>12.2f}\n\n".format(crypto[8]), dt)

    def gen_csv_file(self, parsed_data, csvDir):
        try:
            with open("{}.csv".format(csvDir), "a", newline="") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["排行", "名称", "简写", "价格", "市值", "交易量", "时涨跌幅", "日涨跌幅",
                                 "周涨跌幅", "月涨跌幅", "年涨跌幅", "15分涨跌幅", "交易量/市值"])

                for tup in parsed_data[::-1]:
                    writer.writerow([tup[0], tup[1], tup[2], tup[3], tup[4], tup[5], tup[6]])
        except IOError:
            pass


class SignalStore(QObject):
    label_update = pyqtSignal(str)
    pgsbar_update = pyqtSignal(int)
    table_update = pyqtSignal(list, int)


sigs = SignalStore()
stats_spider = StatsSpider()


class MainWindow():
    def __init__(self):
        sigs.label_update.connect(self.set_label_text)
        sigs.pgsbar_update.connect(self.set_pgsbar_value)
        sigs.table_update.connect(self.set_table_text)

        self.ui = uic.loadUi("CryptoTrends.ui")

        self.ref_time_remain = self.ui.label_refresh_time

        self.progress_bar = self.ui.pgsBar_refresh_time
        self.progress_bar.setRange(0, 100)

        self.ui.cBox_range.addItems(["20", "30", "50"])
        self.ui.cBox_range.currentIndexChanged.connect(self.show_table)

        self.ui.raBtn_HAsc.setChecked(True)
        self.ui.btngrp_screen.buttonClicked.connect(self.show_table)
        self.screen_selection = ""

        self.ui.lE_refresh.setPlaceholderText('请输入数字')

        self.ui.cBox_refresh.addItems(["小时", "分钟", "秒"])

        self.ui.confirm_btn.clicked.connect(self.reschedule_refresh)

        self.ui.table_trend.setColumnCount(9)
        self.ui.table_trend.setHorizontalHeaderLabels(
            ["排行", "名称", "简写", "价格", "市值", "交易量", "时涨跌幅", "日涨跌幅", "交易量/市值"]
        )
        self.ui.table_trend.setColumnWidth(0, 80)
        self.ui.table_trend.setColumnWidth(1, 260)
        self.ui.table_trend.setColumnWidth(2, 100)
        self.ui.table_trend.setColumnWidth(3, 100)
        self.ui.table_trend.setColumnWidth(4, 152)
        self.ui.table_trend.setColumnWidth(5, 152)
        self.ui.table_trend.setColumnWidth(6, 100)
        self.ui.table_trend.setColumnWidth(7, 100)
        self.ui.table_trend.setColumnWidth(8, 100)
        self.ui.table_trend.horizontalHeader().setStretchLastSection(True)
        self.ui.table_trend.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        #self.ui.table_trend.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        #self.ui.table_trend.horizontalHeader().resizeSections(QHeaderView.ResizeToContents)

        self.opacity_animation = QPropertyAnimation(self.ui, b"windowOpacity")
        self.opacity_animation.setDuration(3000)
        self.ui.closeEvent = self.closeEvent

        self.parsed_data = []
        self.ref_status = False
        self.lock = Lock()
        self.sche = self.task_scheduler()
        self.ref_time_string = "1:0:0"
        self.task_main()
        self.fade_in()


    def fade_in(self):
        try:
            self.opacity_animation.finished.disconnect(self.ui.close)  # 尝试先取消动画完成后关闭窗口的信号
        except:
            pass
        self.opacity_animation.stop()
        # 透明度范围从0逐渐增加到1
        self.opacity_animation.setStartValue(0)
        self.opacity_animation.setEndValue(1)
        self.opacity_animation.start()


    def fade_out(self):
        self.opacity_animation.stop()
        self.opacity_animation.finished.connect(self.ui.close)  # 动画完成则关闭窗口
        # 透明度范围从1逐渐减少到0
        self.opacity_animation.setStartValue(1)
        self.opacity_animation.setEndValue(0)
        self.opacity_animation.start()


    def closeEvent(self, event):
        result = QMessageBox.question(
            self.ui, "关闭提示", "您确定要关闭 【Trending on Cryptos】 吗?", QMessageBox.Yes | QMessageBox.No)
        if result == QMessageBox.Yes:
            self.fade_out()
            event.accept()
        else:
            event.ignore()


    def emit_ref_signal(self, tstring, lock):
        def str2countdown(tstring):
            lock.acquire()
            counter = 0
            hour, minute, second = tstring.split(":")
            hour, minute, second = int(hour), int(minute), int(second)
            total_seconds = hour * 60 * 60 + minute * 60 + second
            seconds = total_seconds
            while seconds:
                seconds -= 1
                time.sleep(1)
                hour = seconds // 3600
                minute = (seconds % 3600) // 60
                second = seconds - hour * 3600 - minute * 60

                counter += 1
                progress = counter / total_seconds
                progress = round(progress * 100) if progress > 0.01 else 1
                sigs.pgsbar_update.emit(progress)

                text = "距离下次刷新：{:0>2d}:{:0>2d}:{:0>2d}".format(hour, minute, second)
                sigs.label_update.emit(text)

                if self.ref_status:
                    self.ref_status = False
                    lock.release()
                    break

            if (hour == 0) and (minute == 0) and (second == 0):
                lock.release()

        ref_info_thread = Thread(target=str2countdown, args=(tstring, ), daemon=True)
        ref_info_thread.start()


    def set_label_text(self, text):
        self.ref_time_remain.setText(text)


    def set_pgsbar_value(self, value):
        self.progress_bar.setValue(value)


    def set_table_text(self, parsed_data, screen_selection):
        self.ui.table_trend.setRowCount(0)
        line_no = 0

        for crypto in parsed_data[screen_selection]:
            self.ui.table_trend.insertRow(line_no)

            item_c1 = QTableWidgetItem("{0:s}".format(crypto[1]))
            item_c1.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.ui.table_trend.setItem(line_no, 0, item_c1)

            item_c2 = QTableWidgetItem("{0:s}".format(crypto[0]))
            item_c2.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.ui.table_trend.setItem(line_no, 1, item_c2)

            item_c3 = QTableWidgetItem("{0:s}".format(crypto[2]))
            item_c3.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.ui.table_trend.setItem(line_no, 2, item_c3)

            item_c4 = QTableWidgetItem("{0:f}".format(crypto[3]))
            item_c4.setTextAlignment(Qt.AlignRight | Qt.AlignCenter)
            self.ui.table_trend.setItem(line_no, 3, item_c4)

            item_c5 = QTableWidgetItem("{0:,d}".format(crypto[5]))
            item_c5.setTextAlignment(Qt.AlignRight | Qt.AlignCenter)
            self.ui.table_trend.setItem(line_no, 4, item_c5)

            item_c6 = QTableWidgetItem("{0:,d}".format(crypto[4]))
            item_c6.setTextAlignment(Qt.AlignRight | Qt.AlignCenter)
            self.ui.table_trend.setItem(line_no, 5, item_c6)

            item_c7 = QTableWidgetItem("{0:.2%}".format(crypto[6]))
            item_c7.setTextAlignment(Qt.AlignRight | Qt.AlignCenter)
            self.ui.table_trend.setItem(line_no, 6, item_c7)

            item_c8 = QTableWidgetItem("{0:.2%}".format(crypto[7]))
            item_c8.setTextAlignment(Qt.AlignRight | Qt.AlignCenter)
            self.ui.table_trend.setItem(line_no, 7, item_c8)

            item_c9 = QTableWidgetItem("{0:.2f}".format(crypto[8]))
            item_c9.setTextAlignment(Qt.AlignCenter | Qt.AlignCenter)
            self.ui.table_trend.setItem(line_no, 8, item_c9)

            item_tuple = (item_c1, item_c2, item_c3, item_c4, item_c5, item_c6, item_c7, item_c8, item_c9)
            if crypto[8] > 5:
                for item in item_tuple:
                    item.setBackground(QtGui.QColor(237, 67, 156))
            elif crypto[8] > 3:
                for item in item_tuple:
                    item.setBackground(QtGui.QColor(166, 228, 227))
            elif crypto[8] > 1:
                for item in item_tuple:
                    item.setBackground(QtGui.QColor(244, 241, 200))
            else:
                pass

            line_no += 1


    def show_table(self):
        self.screen_selection = self.ui.btngrp_screen.checkedButton().text()
        data_range = int(self.ui.cBox_range.currentText())
        sorted_data = stats_spider.data_sorter(self.parsed_data, data_range)

        if self.screen_selection == "时涨跌幅_ASC":
            sigs.table_update.emit(sorted_data, 0)
        elif self.screen_selection == "时涨跌幅_DESC":
            sigs.table_update.emit(sorted_data, 1)
        elif self.screen_selection == "日涨跌幅_ASC":
            sigs.table_update.emit(sorted_data, 2)
        else:
            sigs.table_update.emit(sorted_data, 3)


    def detect_int_refresh(self, int_ref, ref_measure):
        try:
            int_ref = int(int_ref)
        except ValueError:
            QMessageBox.warning(self.ui, "警告", "输入值必须为数字！")
            return False

        if ref_measure == "小时" and int_ref > 23:
            QMessageBox.warning(self.ui, "警告", "当刷新间隔为[小时]时,输入值必须小于等于23！")
        elif ref_measure == "分钟" and int_ref > 59:
            QMessageBox.warning(self.ui, "警告", "当刷新间隔为[分钟]时,输入值必须小于等于59！")
        elif ref_measure == "秒" and int_ref > 59:
            QMessageBox.warning(self.ui, "警告", "当刷新间隔为[秒]时,输入值必须小于等于59！")
        else:
            return True


    def reschedule_refresh(self):
        int_ref = self.ui.lE_refresh.text()
        ref_measure = self.ui.cBox_refresh.currentText()

        if self.detect_int_refresh(int_ref, ref_measure):
            int_ref = int(int_ref)
            self.ref_status = True

            if ref_measure == "小时":
                self.sche.reschedule_job(job_id="job_cycle", trigger="interval", hours=int_ref)
                self.ref_time_string = "{}:0:0".format(int_ref)
                self.emit_ref_signal(self.ref_time_string, self.lock)
            elif ref_measure == "分钟":
                self.sche.reschedule_job(job_id="job_cycle", trigger="interval", minutes=int_ref)
                self.ref_time_string = "0:{}:0".format(int_ref)
                self.emit_ref_signal(self.ref_time_string, self.lock)
            else:
                self.sche.reschedule_job(job_id="job_cycle", trigger="interval", seconds=int_ref)
                self.ref_time_string = "0:0:{}".format(int_ref)
                self.emit_ref_signal(self.ref_time_string, self.lock)
        else:
            pass


    def task_main(self):
        raw_data = stats_spider.get_html(stats_spider.url_dict["cryptoBubbles"])
        self.parsed_data = stats_spider.data_parser(raw_data)
        sorted_data = stats_spider.data_sorter(self.parsed_data)
        self.show_table()
        self.emit_ref_signal(self.ref_time_string, self.lock)
        stats_spider.gen_txt_file(sorted_data)


    def task_scheduler(self):
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s'",
            datefmt='%a, %d %b %Y %H:%M:%S',
            filename="log1.txt",
            filemode="a"
        )

        jobstores = {
            "default": MemoryJobStore()  # 内存作为作业存储器时，重新运行程序相当于初次运行，不受上次运行进度影响
        }
        executors = {
            "default": ThreadPoolExecutor(5)
        }
        job_defaults = {
            "coalesce": False,
            "max_instances": 3
        }
                                                                            # replace_existing=True
        scheduler = QtScheduler(jobstores=jobstores, executors=executors, job_defaults=job_defaults)

        def sche_listener(event):
            if event.exception:
                print("Sche_listener monitored something!")
            else:
                pass

        scheduler.add_job(self.task_main, "cron", hour="00-23", minute="00", second="00", id="job_cycle")
        scheduler.add_listener(sche_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
        scheduler._logger = logging

        try:
            scheduler.start()
        except SystemExit:
            print("Error!")
            exit()

        return scheduler





if __name__ == "__main__":
    app = QApplication(sys.argv)
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
        'CompanyName.ProductName.SubProduct.VersionInformation'
    )
    app.setWindowIcon(QIcon("count.ico"))
    mainWindow = MainWindow()
    mainWindow.ui.show()
    sys.exit(app.exec_())

