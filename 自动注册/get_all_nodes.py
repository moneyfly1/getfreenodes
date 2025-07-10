import requests
import json
import base64
import os
import time
import random

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
URLS_FILE = os.path.join(BASE_DIR, 'getnodelist.txt')
OUTPUT_FILE = os.path.abspath(os.path.join(BASE_DIR, '../nodes/nodes.txt'))

def read_urls(file_path):
    if not os.path.exists(file_path):
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('')
        print(f'未找到 {file_path}，已自动创建空文件，请填写节点接口后重新运行。')
        exit(1)
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]
    if not lines:
        print(f'{file_path} 为空，请填写节点接口后重新运行。')
        exit(1)
    return lines

def need_email_code(html_text):
    return 'email_code' in html_text or '邮箱验证码' in html_text

def has_slider_or_cloudflare(html_text):
    keywords = ['slider', 'geetest', 'cloudflare', 'cf-challenge', '验证码']
    return any(kw in html_text.lower() for kw in keywords)

def generate_gmail():
    return f'auto{int(time.time())%100000}{random.randint(100,999)}@gmail.com'

def generate_password():
    chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    return ''.join(random.choice(chars) for _ in range(10))

def auto_register(session, base_url, email, password):
    register_url = base_url + '/auth/register'
    try:
        page = session.get(register_url)
        html = page.text
        if need_email_code(html):
            print(f'[register] {register_url} 需要邮箱验证码，跳过注册')
            return False
        if has_slider_or_cloudflare(html):
            print(f'[register] {register_url} 检测到滑动/Cloudflare验证，尝试自动通过（当前直接跳过）')
            return False
    except Exception as e:
        print(f'[register] 获取注册页面失败: {e}')
        return False
    data = {
        'email': email,
        'passwd': password,
        'repasswd': password,
        'invite_code': '',
        'email_code': '',
    }
    resp = session.post(register_url, data=data)
    print(f'[register] {register_url} 返回: {resp.text}')
    return resp.status_code == 200 and ('成功' in resp.text or '注册成功' in resp.text)

def auto_login(session, base_url, email, password):
    login_url = base_url + '/auth/login'
    data = {
        'email': email,
        'passwd': password,
        'remember_me': 'on'
    }
    resp = session.post(login_url, data=data)
    print(f'[login] {login_url} 返回: {resp.text}')
    return resp.status_code == 200

def get_nodes(session, base_url):
    node_url = base_url + '/getnodelist'
    resp = session.get(node_url)
    print(f'[getnodelist] {node_url} 返回: {resp.text[:100]}...')
    if resp.status_code == 200:
        return resp.json()
    return None

def process_node_data(data):
    links = []
    if not data or data.get('ret') != 1 or not data.get('nodeinfo'):
        return links
    nodeinfo = data['nodeinfo']
    if 'nodes_muport' in nodeinfo and nodeinfo['nodes_muport'] and 'user' in nodeinfo['nodes_muport'][0]:
        user_info = nodeinfo['nodes_muport'][0]['user']
    else:
        user_info = nodeinfo['user']
    uuid = user_info['uuid']
    ss_password = user_info['passwd']
    method = user_info['method']
    for node in nodeinfo['nodes']:
        raw_node = node['raw_node']
        if ';port=' in raw_node['server']:
            server = raw_node['server'].split(';port=')[0]
            port = raw_node['server'].split('#')[1]
            ss_link = f'{method}:{ss_password}@{server}:{port}'
            ss_link_encoded = base64.b64encode(ss_link.encode()).decode()
            final_link = f'ss://{ss_link_encoded}#{raw_node["name"]}'
            links.append(final_link)
        elif raw_node['server'].count(';') >= 3:
            server_parts = raw_node['server'].split(';')
            server = server_parts[0]
            port = server_parts[1]
            aid = server_parts[2] if len(server_parts) > 2 else '64'
            net = server_parts[3] if len(server_parts) > 3 else 'ws'
            host = ''
            path = ''
            if len(server_parts) > 5 and server_parts[5]:
                for part in server_parts[5].split('|'):
                    if part.startswith('path='):
                        path = part[5:]
                    elif part.startswith('host='):
                        host = part[5:]
            vmess_config = {
                "v": "2",
                "ps": raw_node["name"],
                "add": server,
                "port": port,
                "id": uuid,
                "aid": str(aid),
                "net": net,
                "type": "none",
                "host": host,
                "path": path,
                "tls": ""
            }
            vmess_link = base64.b64encode(json.dumps(vmess_config).encode()).decode()
            final_link = f'vmess://{vmess_link}'
            links.append(final_link)
    return links

def main():
    try:
        urls = read_urls(URLS_FILE)
        all_links = []
        for url in urls:
            print(f'处理: {url}')
            base_url = url.split('/getnodelist')[0]
            session = requests.Session()
            try:
                resp = session.get(url, timeout=10)
                try:
                    data = resp.json()
                except Exception as e:
                    print(f'[跳过] {url} 返回内容不是JSON: {e}')
                    continue
            except Exception as e:
                print(f'[跳过] 访问 {url} 失败: {e}')
                continue
            # 只在 ret == -1 时注册，否则直接跳过注册
            if data.get('ret') == -1:
                email = generate_gmail()
                password = generate_password()
                if auto_register(session, base_url, email, password):
                    if auto_login(session, base_url, email, password):
                        data = get_nodes(session, base_url)
                        links = process_node_data(data)
                        all_links.extend(links)
                        print(f'[注册+获取] {url} 成功，已添加节点')
                    else:
                        print(f'[跳过] {url} 登录失败')
                else:
                    print(f'[跳过] {url} 注册失败或需要验证码/Cloudflare')
            else:
                # 只处理 ret==1 的情况
                if data.get('ret') == 1:
                    links = process_node_data(data)
                    all_links.extend(links)
                    print(f'[获取] {url} 成功，已添加节点')
                else:
                    print(f'[跳过] {url} 未返回有效节点(ret!=1)')
        # 保存所有节点到 nodes/nodes.txt
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(all_links))
        print(f'已保存 {len(all_links)} 条节点到 {OUTPUT_FILE}')
    except Exception as e:
        print(f'运行出错: {e}')
        # 不再 exit(1)，而是继续

if __name__ == '__main__':
    main() 