from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from gevent import sleep 

# Flask 앱 및 SocketIO 객체 생성
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_super_secret_key'
socketio = SocketIO(app, async_mode='gevent') 

# 게임 상태 변수 초기화
BOARD_SIZE = 9
EMPTY = 0
GAME_BOARD = [EMPTY] * BOARD_SIZE
CURRENT_TURN = None
players = []
GAME_ACTIVE = False
WINNING_COMBOS = [
    (0, 1, 2), (3, 4, 5), (6, 7, 8), # 가로
    (0, 3, 6), (1, 4, 7), (2, 5, 8), # 세로
    (0, 4, 8), (2, 4, 6)             # 대각선
]

# 승리 판정 함수
def check_winner(board, player_mark):
  for combo in WINNING_COMBOS:
    if all(board[i] == player_mark for i in combo):
      return True
  return False

# 루트 URL ('/') - HTML 파일 렌더링
@app.route('/')
def index():
  return render_template('index.html')

# 웹 소켓 이벤트 처리 : 클라이언트가 연결되었을 때
@socketio.on('connect')
def handle_connect(*args):
  global players, GAME_ACTIVE, GAME_BOARD, CURRENT_TURN

  if request.sid in players or len(players) >= 2:
      return

  if len(players) == 0:
    players.append(request.sid)
    emit('message', {'data': '연결 성공! 당신은 1번째 플레이어(X)입니다. 상대방을 기다리는 중...'}, room=request.sid)
    return

  if len(players) == 1 and request.sid != players[0]:
    players.append(request.sid)
    
    P1_SID = players[0]
    P2_SID = players[1]
    
    GAME_ACTIVE = True
    GAME_BOARD = [EMPTY] * BOARD_SIZE
    CURRENT_TURN = P1_SID
    
    emit('message', {'data': '연결 성공! 당신은 2번째 플레이어(O)입니다.'}, room=P2_SID)

    socketio.emit('game_start', {'turn': CURRENT_TURN, 'mark': 'X'}, room=P1_SID)
    socketio.emit('game_start', {'turn': CURRENT_TURN, 'mark': 'O'}, room=P2_SID)
    print("게임 시작!")
    return

# 웹 소켓 이벤트 처리 : 클라이언트가 돌을 놓았을 때
@socketio.on('place_piece')
def handle_place_piece(data):
    global GAME_ACTIVE, GAME_BOARD, CURRENT_TURN
    player_id = request.sid

    # 1. 게임 상태 및 턴 검사 (생략)
    if not GAME_ACTIVE : return
    if player_id != CURRENT_TURN:
        emit('message', {'data' :'당신의 턴이 아닙니다.'}, room=player_id)
        return
    cell_index = int(data['id']) - 1
    if not(0 <= cell_index < BOARD_SIZE) or GAME_BOARD[cell_index] != EMPTY:
        emit('message', {'data': '이미 놓여진 칸입니다.'}, room=player_id)
        return

    # 2. 돌 놓기 및 마크 결정
    mark = 1 if player_id == players[0] else 2
    mark_char = 'X' if mark == 1 else 'O'
    GAME_BOARD[cell_index] = mark

    # 3. 보드 업데이트 이벤트를 승패 판정 전에 먼저 전송
    next_player_id = players[1] if player_id == players[0] else players[0]
    
    socketio.emit('board_update', {
        'id': cell_index + 1,
        'mark': mark_char,
        'next_turn': next_player_id
    }, room='')

    # gevent sleep을 사용하여 클라이언트가 board_update를 처리할 시간 확보
    sleep(0.01)  

    # 4. 승리 판정
    if check_winner(GAME_BOARD, mark):
        winner_mark = mark_char
        loser_mark = 'O' if winner_mark == 'X' else 'X'
        
        # 🚨 승자와 패자 마크를 모두 전송
        socketio.emit('game_end', {
            'winner': winner_mark,
            'loser': loser_mark,
            'type': 'win'
        }, room='')
        GAME_ACTIVE = False
        return

    # 5. 무승부 판정
    if EMPTY not in GAME_BOARD:
        socketio.emit('game_end', {
            'winner': 'DRAW',
            'type': 'draw'
        }, room='')
        GAME_ACTIVE = False
        return

    # 6. 턴 넘기기 (승패가 나지 않았을 때만 실행)
    CURRENT_TURN = next_player_id

# 웹 소켓 이벤트 처리 : 클라이언트 연결 해제
@socketio.on('disconnect')
def handle_disconnect():
  global players, GAME_ACTIVE, GAME_BOARD, CURRENT_TURN
  if request.sid in players:
    players.remove(request.sid)
    GAME_ACTIVE = False
    GAME_BOARD = [EMPTY] * BOARD_SIZE
    CURRENT_TURN = None
    print(f"플레이어 연결 해제 : {request.sid}. 현재 {len(players)}명 남음.")
    socketio.emit('message', {'data': '상대방이 나갔습니다. 게임이 종료됩니다.'}, room='')

# Flask 개발 서버 실행
if __name__ == '__main__':
  socketio.run(app, host='0.0.0.0', port=5000, debug=False)