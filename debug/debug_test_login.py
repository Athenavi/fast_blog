import json

import requests


# 测试登录API
def test_login():
    url = "http://localhost:8000/api/v1/auth/login"
    
    # 测试数据
    payload = {
        "email": "test@example01.com",
        "password": "123456"
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        # 如果请求成功，打印cookies
        if response.status_code == 200:
            print("\nCookies set:")
            for cookie in response.cookies:
                print(f"  {cookie.name}: {cookie.value}")
                
    except requests.exceptions.ConnectionError:
        print("无法连接到服务器，请确保后端服务正在运行")
    except Exception as e:
        print(f"请求过程中出现错误: {str(e)}")

if __name__ == "__main__":
    test_login()