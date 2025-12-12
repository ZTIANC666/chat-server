import asyncio
import websockets
import json
from datetime import datetime
from websockets.server import serve
from websockets.exceptions import ConnectionClosed
import http

connected_clients = {}

async def handle_client(websocket, path):
    client_id = id(websocket)
    username = None
    
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                msg_type = data.get('type')
                
                if msg_type == 'join':
                    username = data.get('username', f'用户{client_id}')
                    connected_clients[client_id] = {
                        'websocket': websocket,
                        'username': username
                    }
                    
                    await broadcast({
                        'type': 'system',
                        'content': f'{username} 加入了聊天室',
                        'timestamp': datetime.now().strftime('%H:%M:%S')
                    })
                    
                    await broadcast({
                        'type': 'user_list',
                        'users': [client['username'] for client in connected_clients.values()]
                    })
                    
                    print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] {username} 已连接')
                
                elif msg_type == 'message':
                    if username:
                        await broadcast({
                            'type': 'message',
                            'username': username,
                            'content': data.get('content', ''),
                            'timestamp': datetime.now().strftime('%H:%M:%S')
                        })
                        
            except json.JSONDecodeError:
                print(f'[错误] 无效的JSON消息: {message}')
            except Exception as e:
                print(f'[错误] 处理消息时出错: {e}')
    
    finally:
        if client_id in connected_clients:
            username = connected_clients[client_id]['username']
            del connected_clients[client_id]
            
            await broadcast({
                'type': 'system',
                'content': f'{username} 离开了聊天室',
                'timestamp': datetime.now().strftime('%H:%M:%S')
            })
            
            await broadcast({
                'type': 'user_list',
                'users': [client['username'] for client in connected_clients.values()]
            })
            
            print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] {username} 已断开')

async def broadcast(message):
    if connected_clients:
        message_json = json.dumps(message, ensure_ascii=False)
        await asyncio.gather(
            *[client['websocket'].send(message_json) 
              for client in connected_clients.values()],
            return_exceptions=True
        )

async def health_check(path, request_headers):
    if path == "/health":
        return http.HTTPStatus.OK, [], b"OK\n"
    return None

async def main():
    import os
    port = int(os.environ.get('PORT', 8765))
    print(f'WebSocket服务器启动在端口 {port}')
    print(f'服务器时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('等待客户端连接...\n')
    
    async with serve(
        handle_client, 
        '0.0.0.0', 
        port,
        process_request=health_check
    ):
        await asyncio.Future()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('\n服务器已关闭')
