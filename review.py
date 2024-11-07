#!/usr/bin/env python
# -*- encoding:utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import csv
import os

import requests
from datetime import datetime, timedelta
from io import BytesIO

import dateutil.parser
from googleapiclient import discovery, http
from googleapiclient.errors import HttpError
from oauth2client.service_account import ServiceAccountCredentials

import settings
import secrets


def lambda_handler(event, context):
    webhook_url = secrets.slack_webhook_url  # 使用 Webhook URL
    print("Current time (UTC) is {0}".format(datetime.utcnow()))
    for app in settings.apps:
        print("Processing reviews for ", app)
        app_filename = construct_filename(app)
        file_buf = BytesIO()
        all_reviews = []

        # 檢查 download_report 是否成功
        if not download_report(secrets.google_bucket, app_filename, file_buf):
            print(f"Failed to download report for {app}. Terminating function.")
            return  # 結束函數，直接返回

        print("Downloaded report")
        file_buf.seek(0)
        all_reviews.extend(process_reviews(file_buf, webhook_url))

        if not all_reviews:
            no_new_reviews_message = f"No new Play Store reviews or ratings for {app}"
            print(no_new_reviews_message)
            send_slack_message(webhook_url, no_new_reviews_message)
        else:
            print("Posting reviews for " + app)
            send_slack_message(webhook_url, f"New reviews or ratings for {app}")
            for review in all_reviews:
                send_slack_message(webhook_url, review)
        print("\n\n")


def construct_filename(app_package):
    format_string = 'reviews_{0}_{1}{2}.csv'
    current_date = datetime.utcnow()
    return format_string.format(app_package, current_date.year, '%02d' % current_date.month)


def download_report(bucket, filename, out_file):
    service = create_service()

    full_path_filename = 'reviews/' + filename
    req = service.objects().get_media(bucket=bucket, object=full_path_filename)
    downloader = http.MediaIoBaseDownload(out_file, req)

    done = False
    while not done:
        try:
            status, done = downloader.next_chunk()
        except HttpError as e:
            print("Failed to download ", e)
            return False
        print("Download {}%.".format(int(status.progress() * 100)))

    return True


def create_service():
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(
        settings.google_credentials,
        scopes='https://www.googleapis.com/auth/devstorage.read_only'
    )
    return discovery.build('storage', 'v1', credentials=credentials)


def process_reviews(file_buf, webhook_url):
    # 讀取已發送的評論 ID
    sent_reviews = load_sent_reviews()
    decoded_csv_file = file_buf.read().decode('utf-16')
    csv_reader = csv.reader(decoded_csv_file.splitlines(), delimiter=',')
    next(csv_reader, None)  # skip the headers
    all_reviews = []
    for row in csv_reader:
        print(row)
        submitted_at = row[7]  # 假設使用提交時間作為唯一 ID

        # 檢查評論是否已經發送過
        if submitted_at in sent_reviews:
            print(f"Ignoring already sent review with timestamp {submitted_at}")
            continue

        # 僅發送指定天數內的評論
        if (datetime.utcnow() - dateutil.parser.parse(submitted_at, ignoretz=True)) > timedelta(days=settings.days_in_past):
            print("Ignoring review with timestamp " + submitted_at)
            continue

        app_name = row[0]
        version = row[2]
        device = row[4]
        rating = row[9]
        title = row[10]
        text = row[11]
        url = row[15]

        # 僅在有文本時才創建消息
        if text.strip():
            msg = format_message(title, text, submitted_at, rating, device, version, url, app_name)
            all_reviews.append(msg)

        # 保存這條評論的 ID
        save_sent_review(submitted_at,text)

    return all_reviews

# 用於存儲已發送評論 ID 的文件
SENT_REVIEWS_FILE = 'sent_reviews.txt'

def load_sent_reviews():
    """從文件中加載已發送的評論（僅使用 ID 進行比對）"""
    if not os.path.exists(SENT_REVIEWS_FILE):
        return set()
    with open(SENT_REVIEWS_FILE, 'r') as file:
        return set(line.strip().split('|')[0] for line in file)

def save_sent_review(review_id, text):
    """將已發送的評論保存到文件中，包含 ID、時間和文字"""
    with open(SENT_REVIEWS_FILE, 'a') as file:
        file.write(f"{review_id}|{text}\n")



def format_message(title, text, submitted_at, rating, device, version, url, app_name):
    stars = ''

    for i in range(int(rating)):
        stars += '★'
    for i in range(5 - int(rating)):
        stars += '☆'

    if not url:
        format_rating = 'Application: {4}\nRating: {0}\nSubmitted at: {1}\nDevice: {2}\nVersion: {3}\n'
        return format_rating.format(stars, submitted_at, device, version, app_name)

    format_review = 'Application: {7}\nRating: {3}\nText: {0} {1}\nSubmitted at: {2}\nDevice: {4}\nVersion: {5}\nURL: {6}'
    return format_review.format(title, text, submitted_at, stars, device, version, url, app_name)


def send_slack_message(webhook_url, message):
    # 在每個消息前後添加分隔線
    payload = {"text": f"{message}\n--------------------------"}
    try:
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f"Failed to send message: {e}")

def test_process_reviews_with_local_csv(csv_path, webhook_url):
            # 打開本地 CSV 文件
            with open(csv_path, mode='rb') as file:
                # 將文件讀入 BytesIO，模擬下載到的文件
                file_buf = BytesIO(file.read())

            # 開始處理 CSV 文件並發送評論到 Slack
            all_reviews = process_reviews(file_buf, webhook_url)
            if not all_reviews:
                no_new_reviews_message = "No new reviews in the provided CSV file."
                print(no_new_reviews_message)
                send_slack_message(webhook_url, no_new_reviews_message)
            else:
                send_slack_message(webhook_url, "New reviews from the provided CSV file:")
                for review in all_reviews:
                    send_slack_message(webhook_url, review)



    # 使用本地的 CSV 文件進行測試
# if __name__ == '__main__':
#     local_csv_path = '/Users/hyc/Desktop/reviews_dbx.taiwantaxi_202410.csv'  # 請將此處替換為您的 CSV 文件路徑
#     webhook_url = secrets.slack_webhook_url
#     test_process_reviews_with_local_csv(local_csv_path, webhook_url)


if __name__ == '__main__':
    lambda_handler("", "")
