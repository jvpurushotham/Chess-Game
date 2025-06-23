from flask import Flask, render_template_string, request, jsonify
import chess
import chess.engine
import random
import time

app = Flask(__name__)
board = chess.Board()
mode = "human"
move_history = []

try:
    engine = chess.engine.SimpleEngine.popen_uci("stockfish")
except Exception as e:
    print("Stockfish engine error:", e)
    engine = None

HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Chess Game</title>
  <style>
    html, body {
      height: 100%;
      margin: 0;
      font-family: Arial, sans-serif;
      background-color: #222;
      color: white;
    }

    body {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 10px;
    }

    h1 {
      margin: 10px;
    }

    #controls {
      margin: 10px;
    }

    #container {
      display: flex;
      flex-direction: row;
      flex-wrap: wrap;
      justify-content: center;
      width: 100%;
      max-width: 1200px;
    }

    #chessboard {
      display: grid;
      grid-template-columns: repeat(8, 1fr);
      width: 80vmin;
      height: 80vmin;
      max-width: 80vh;
      max-height: 80vh;
      border: 4px solid white;
    }

    #history {
      width: 250px;
      margin-left: 20px;
      background: #333;
      border: 2px solid white;
      padding: 10px;
      overflow-y: auto;
      height: 78vmin;
    }

    .square {
      width: 100%;
      height: 100%;
    }

    .white {
      background-color: #f0d9b5;
    }

    .black {
      background-color: #b58863;
    }

    .piece {
      width: 100%;
      height: 100%;
      background-size: contain;
      background-repeat: no-repeat;
      background-position: center;
      cursor: grab;
    }

    .selected {
      outline: 3px solid red;
    }

    @media (max-width: 768px) {
      #container {
        flex-direction: column;
        align-items: center;
      }

      #chessboard {
        width: 95vmin;
        height: 95vmin;
      }

      #history {
        width: 90%;
        height: auto;
        margin-left: 0;
        margin-top: 20px;
      }
    }
  </style>
</head>
<body>
  <h1>Chess Game</h1>
  <div id="controls">
    <button onclick="setMode('human')">Play vs Human</button>
    <button onclick="setMode('ai')">Play vs AI</button>
    <button onclick="resetGame()">Reset Game</button>
  </div>
  <div id="container">
    <div id="chessboard"></div>
    <div id="history">
      <h3>Move History</h3>
      <ul id="moveList"></ul>
    </div>
  </div>
  <p id="message"></p>

  <script>
    const PIECE_IMAGES = {
      r: "https://upload.wikimedia.org/wikipedia/commons/f/ff/Chess_rdt45.svg",
      n: "https://upload.wikimedia.org/wikipedia/commons/e/ef/Chess_ndt45.svg",
      b: "https://upload.wikimedia.org/wikipedia/commons/9/98/Chess_bdt45.svg",
      q: "https://upload.wikimedia.org/wikipedia/commons/4/47/Chess_qdt45.svg",
      k: "https://upload.wikimedia.org/wikipedia/commons/f/f0/Chess_kdt45.svg",
      p: "https://upload.wikimedia.org/wikipedia/commons/c/c7/Chess_pdt45.svg",
      R: "https://upload.wikimedia.org/wikipedia/commons/7/72/Chess_rlt45.svg",
      N: "https://upload.wikimedia.org/wikipedia/commons/7/70/Chess_nlt45.svg",
      B: "https://upload.wikimedia.org/wikipedia/commons/b/b1/Chess_blt45.svg",
      Q: "https://upload.wikimedia.org/wikipedia/commons/1/15/Chess_qlt45.svg",
      K: "https://upload.wikimedia.org/wikipedia/commons/4/42/Chess_klt45.svg",
      P: "https://upload.wikimedia.org/wikipedia/commons/4/45/Chess_plt45.svg"
    };

    let draggedFrom = null;
    let clickedFrom = null;

    async function fetchFEN() {
      const res = await fetch('/fen');
      const data = await res.json();
      renderBoard(data.fen);
      renderHistory(data.history);
    }

    function renderHistory(moves) {
      const list = document.getElementById("moveList");
      list.innerHTML = '';
      for (let i = 0; i < moves.length; i += 2) {
        const li = document.createElement("li");
        li.innerText = `${Math.floor(i/2) + 1}. ${moves[i]}${moves[i+1] ? " " + moves[i+1] : ""}`;
        list.appendChild(li);
      }
    }

    function renderBoard(fen) {
      const boardDiv = document.getElementById("chessboard");
      boardDiv.innerHTML = '';
      const rows = fen.split(" ")[0].split("/");
      for (let row = 0; row < 8; row++) {
        let col = 0;
        for (let char of rows[row]) {
          if (!isNaN(char)) {
            for (let i = 0; i < parseInt(char); i++) {
              addSquare(row, col++, '');
            }
          } else {
            addSquare(row, col, char);
            col++;
          }
        }
      }
    }

    function addSquare(row, col, pieceChar) {
      const square = document.createElement("div");
      square.className = "square " + ((row + col) % 2 === 0 ? "white" : "black");
      square.dataset.row = row;
      square.dataset.col = col;
      square.ondrop = drop;
      square.ondragover = allowDrop;
      square.onclick = () => squareClick(row, col);

      if (pieceChar) {
        const piece = document.createElement("div");
        piece.className = "piece";
        piece.style.backgroundImage = `url(${PIECE_IMAGES[pieceChar]})`;
        piece.draggable = true;
        piece.dataset.row = row;
        piece.dataset.col = col;
        piece.ondragstart = drag;
        square.appendChild(piece);
      }

      document.getElementById("chessboard").appendChild(square);
    }

    function squareClick(row, col) {
      if (!clickedFrom) {
        clickedFrom = { row, col };
        highlight(row, col);
      } else {
        const from = toChess(clickedFrom.row, clickedFrom.col);
        const to = toChess(row, col);
        makeMove(from, to);
        clearHighlights();
        clickedFrom = null;
      }
    }

    function highlight(row, col) {
      document.querySelectorAll(".square").forEach(sq => {
        if (sq.dataset.row == row && sq.dataset.col == col) {
          sq.classList.add("selected");
        }
      });
    }

    function clearHighlights() {
      document.querySelectorAll(".square").forEach(sq => sq.classList.remove("selected"));
    }

    function toChess(row, col) {
      return 'abcdefgh'[col] + (8 - row);
    }

    function drag(event) {
      draggedFrom = {
        row: event.target.dataset.row,
        col: event.target.dataset.col
      };
    }

    function allowDrop(event) {
      event.preventDefault();
    }

    async function drop(event) {
      event.preventDefault();
      const toRow = event.currentTarget.dataset.row;
      const toCol = event.currentTarget.dataset.col;
      const from = toChess(draggedFrom.row, draggedFrom.col);
      const to = toChess(toRow, toCol);
      makeMove(from, to);
    }

    async function makeMove(from, to) {
      let promotion = '';
      if ((from[1] === '7' && to[1] === '8') || (from[1] === '2' && to[1] === '1')) {
        promotion = prompt("Promote to (q, r, b, n):", "q");
      }

      const res = await fetch('/move', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ from, to, promotion })
      });
      const data = await res.json();
      document.getElementById("message").innerText = data.message;
      renderBoard(data.fen);
      renderHistory(data.history);
    }

    async function setMode(mode) {
      const res = await fetch('/mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode })
      });
      const data = await res.json();
      document.getElementById("message").innerText = "Mode set to: " + data.mode;
      fetchFEN();
    }

    async function resetGame() {
      const res = await fetch('/reset', { method: 'POST' });
      const data = await res.json();
      document.getElementById("message").innerText = "Game reset.";
      fetchFEN();
    }

    window.onload = fetchFEN;
  </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/fen')
def get_fen():
    return jsonify({'fen': board.fen(), 'history': move_history})

@app.route('/move', methods=['POST'])
def move():
    global board
    data = request.get_json()
    from_sq = data['from']
    to_sq = data['to']
    promotion = data.get('promotion')
    move_str = from_sq + to_sq + (promotion if promotion else '')

    try:
        move = chess.Move.from_uci(move_str)
        if move in board.legal_moves:
            board.push(move)
            move_history.append(move.uci())

            if mode == "ai" and not board.is_game_over():
                time.sleep(0.5)
                if engine:
                    result = engine.play(board, chess.engine.Limit(time=1.0))
                    board.push(result.move)
                    move_history.append(result.move.uci())
                    return jsonify({
                        'fen': board.fen(),
                        'message': f"You moved {move_str}, AI moved {result.move.uci()}",
                        'history': move_history
                    })
                else:
                    legal = list(board.legal_moves)
                    ai_move = random.choice(legal)
                    board.push(ai_move)
                    move_history.append(ai_move.uci())
                    return jsonify({
                        'fen': board.fen(),
                        'message': f"You moved {move_str}, AI moved {ai_move.uci()}",
                        'history': move_history
                    })
            return jsonify({'fen': board.fen(), 'message': f'Move played: {move_str}', 'history': move_history})
        else:
            return jsonify({'fen': board.fen(), 'message': 'Illegal move!', 'history': move_history})
    except Exception as e:
        return jsonify({'fen': board.fen(), 'message': f'Error: {str(e)}', 'history': move_history})

@app.route('/mode', methods=['POST'])
def set_mode():
    global mode, board, move_history
    data = request.get_json()
    board = chess.Board()
    move_history = []
    mode = data['mode']
    return jsonify({'mode': mode})

@app.route('/reset', methods=['POST'])
def reset():
    global board, move_history
    board = chess.Board()
    move_history = []
    return jsonify({'message': 'Game reset'})

if __name__ == '__main__':
    app.run(debug=True)
