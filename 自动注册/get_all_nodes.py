import requests
import json
import base64
import os
import time
import random

def read_urls(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]

def need_email_code(html_text):
    # 简单判断是否有邮箱验证码字段
    return 'email_code' in html_text or '邮箱验证码' in html_text

def has_slider_or_cloudflare(html_text):
    # 检查是否有滑动验证、Cloudflare等
    keywords = ['slider', 'geetest', 'cloudflare', 'cf-challenge', '验证码']
    return any(kw in html_text.lower() for kw in keywords)

def generate_gmail():
    return f'auto{int(time.time())%100000}{random.randint(100,999)}@gmail.com'

def auto_register(session, base_url, email, password):
    register_url = base_url + '/auth/register'
    # 先获取注册页面内容
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
    urls = read_urls('自动注册/getnodelist.txt')
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
            email = generate_gmail()
            password = 'Test123456'
            if auto_register(session, base_url, email, password):
                auto_login(session, base_url, email, password)
                data = get_nodes(session, base_url)
            else:
                print(f'跳过 {url} 的注册')
                continue
        else:
            data = get_nodes(session, base_url)
        links = process_node_data(data)
        all_links.extend(links)
    # 保存所有节点
    output_file = 'nodes/nodes.txt'
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(all_links))
    print(f'已保存 {len(all_links)} 条节点到 {output_file}')

if __name__ == '__main__':
    main() 