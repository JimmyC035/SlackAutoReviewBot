
---

# Play Store 評論通知 App

這是一個 Python 應用程式，用於從 Google Play Store 獲取評論藉由 Slack bot (Webhook) 發送到 Slack，幫助開發者追蹤使用者評論。

## 功能

- 獲取應用程式的 Google Play Store 評論。
- 格式化評論訊息並發送至指定的 Slack 頻道。
- 記錄已發送的評論，防止重複發送。
- 紀錄生成文件檔案可供查看評論以及評論時間。

---

## 需求

- **Python 3.0+**
- **一台持續運行的主機**
- **Google Cloud** 和 **Google Play Console** 權限：
  - **Google Cloud Storage** 權限：透過 Service Account 進行設置，用於存取 Play Console 的報告文件。
  - **Play Console** 權限：在 Play Console 中為服務帳戶配置相應的權限，其中 **"View app information"** 權限需設置為 **"Global"**。
  - 詳細說明請參考[官方文件](https://support.google.com/googleplay/android-developer/answer/6135870#export&zippy=%2Csee-an-example-python%2Cdownload-reports-using-a-client-library-and-service-account)。
  
- **Slack bot (Webhook)**：用於發送通知至指定的 Slack 頻道。
  - 有關配置 Slack bot 的詳細步驟，請參考此[教學](https://medium.com/wehkamp-techblog/dont-use-slack-incoming-webhooks-app-creation-is-dead-simple-af9ea8ff41da)。

---

## 使用方法

1. 創建 Google Cloud Service Account 並下載 JSON 憑證文件。根據需要在 Play Console 設置權限，參考：[Play Console 設置權限說明](#play-console-權限設置)。
2. 配置 `settings.py` 和 `secrets.py` 文件，填入相關的 Slack Webhook 和 Google Cloud Storage 配置。
3. 執行主程式：
   ```zsh
   python review.py
   ```
    若需每天自動執行，例如在每天上午 10:00，可以使用 `cron` 定期執行。
    ```zsh
    crontab -e ## 打開設定
    0 10 * * * /path/to/python /path/to/review.py ## 加入這行
    crontab -l ## 確定有設定成功
    ```
---

## 配置

### `settings.py`
- **`apps`**：要查看評論的 Google Play 應用名稱列表。
- **`google_credentials`**：Google Cloud Service Account 憑證文件（JSON 格式）。
- **`days_in_past`**：抓取幾天內的評論。

### `secrets.py`
- **`slack_webhook_url`**：Slack Incoming Webhook URL。
- **`google_bucket`**：Google Cloud Storage 的 Bucket ID， Play Console 報告位置 URI。
  ``` 
  例：pubsite_prod_xxxxxxxxxxxxxxxx
  ```


## 程式碼概述

### 主要組件

1. **`lambda_handler`**：處理評論的主函數，包含以下步驟：
   - 獲取最新的 Play Store 評論。
   - 基於 `review_id` 過濾重複評論。
   - 整理評論資訊並發送到 Slack。

2. **`process_reviews`**：處理每條評論，檢查是否已發送過，並格式化以便發送到 Slack。

3. **`load_sent_reviews` 及 `save_sent_review`**：載入和儲存已發送的評論 `review_id`，以避免重複通知。

## 輸出範例

當找到新評論時，將以下格式發送至 Slack：

```
-------------
New reviews or ratings for com.example
-------------
Application: com.example
Rating: ★★★☆☆
Text: 使用者評論內容...
Submitted at: 2024-11-01T06:20:49Z
Device: ASUS_AI2203
Version: 9.21.0
URL: http://play.google.com/review-link
-------------
```
---


## Play Console 權限設置

#### 步驟 1：建立服務帳戶

1. 打開 Google Developers Console（需使用與 Google Play Console 相同的帳戶登入）。
2. 選擇專案，若無專案可點擊「建立專案」。
3. 前往「Navigation Menu >  IAM & Admin  > Service Accounts > Create Service Account」。
4. 建立完成後，進入「Actions > Manage keys > ADD KEY > JSON >  Create」，下載 JSON 憑證檔案，貼到 `google-auth.json`。
5. 複製服務帳戶的電子郵件地址（例如 `accountName@project.iam.gserviceaccount.com`）。

#### 步驟 2：將服務帳戶新增至 Google Play Console

1. 打開 Google Play Console。
2. 前往「Menu > Users & Permissions >  Invite new user.」。
3. 輸入 Service Account 名稱，並設定 roles : Storage object admin / Storage object viewer。
4. 選擇 View app information and download bulk reports (read-only) 的權限。

---
## 問題排除

- **403 Forbidden**：確保服務帳戶在 Google Play Console 和 Google Cloud Storage 中具有正確的權限。

    ****有時候權限設定完成後，可能需要等待一天才能生效，請耐心等待後再進行測試。****

- **重複評論**：如果出現重複評論，請確保 `review_id` 已正確記錄於 `sent_reviews.txt` 文件中。

---