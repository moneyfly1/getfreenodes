import requests
import json
import base64
import os
import time

URLS_FILE = '自动注册/getnodelist.txt'
OUTPUT_FILE = '自动注册/nodes.txt'

def read_urls(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]

def auto_register(session, base_url, email, password):
    # 假设注册接口为 /auth/register，实际请根据网站调整
    register_url = base_url + '/auth/register'
    data = {
        'email': email,
        'passwd': password,
        'repasswd': password,
        'invite_code': '',  # 有邀请码可填写
        'email_code': '',   # 有邮箱验证码可填写
    }
    resp = session.post(register_url, data=data)
    print(f'[register] {register_url} 返回: {resp.text}')
    return resp.status_code == 200

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
        # SS节点
        if ';port=' in raw_node['server']:
            server = raw_node['server'].split(';port=')[0]
            port = raw_node['server'].split('#')[1]
            ss_link = f'{method}:{ss_password}@{server}:{port}'
            ss_link_encoded = base64.b64encode(ss_link.encode()).decode()
            final_link = f'ss://{ss_link_encoded}#{raw_node["name"]}'
            links.append(final_link)
        # VMESS节点
        elif raw_node['server'].count(';') >= 3:
            server_parts = raw_node['server'].split(';')
            server = server_parts[0]
            port = server_parts[1]
            aid = server_parts[2] if len(server_parts) > 2 else '64'
            net = server_parts[3] if len(server_parts) > 3 else 'ws'
            # 解析path和host
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
    urls = read_urls(URLS_FILE)
    all_links = []
    for url in urls:
        print(f'处理: {url}')
        base_url = url.split('/getnodelist')[0]
        session = requests.Session()
        resp = session.get(url)
        try:
            data = resp.json()
        except Exception:
            data = {}
        if data.get('ret') == -1:
            # 自动注册和登录
            email = f'auto{int(time.time())%100000}@test.com'
            password = 'Test123456'
            auto_register(session, base_url, email, password)
            auto_login(session, base_url, email, password)
            data = get_nodes(session, base_url)
        else:
            # 已登录或无需注册
            data = get_nodes(session, base_url)
        links = process_node_data(data)
        all_links.extend(links)
    # 保存所有节点
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(all_links))
    print(f'已保存 {len(all_links)} 条节点到 {OUTPUT_FILE}')

if __name__ == '__main__':
    main() 