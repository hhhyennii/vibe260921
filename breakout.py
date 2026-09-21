import tkinter as tk
import random

WIDTH = 600
HEIGHT = 500
PADDLE_WIDTH = 100
PADDLE_HEIGHT = 15
BALL_SIZE = 15
BRICK_ROWS = 5
BRICK_COLS = 8
BRICK_WIDTH = WIDTH // BRICK_COLS
BRICK_HEIGHT = 25
BRICK_COLORS = ["#e63946", "#f1a208", "#ffd60a", "#52b788", "#4895ef"]


class Breakout:
    def __init__(self, root):
        self.root = root
        self.root.title("블럭깨기")
        self.root.resizable(False, False)

        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg="black")
        self.canvas.pack()

        self.score = 0
        self.lives = 3
        self.running = False
        self.game_over = False

        self.score_text = self.canvas.create_text(
            50, 15, text="Score: 0", fill="white", font=("Arial", 12)
        )
        self.lives_text = self.canvas.create_text(
            WIDTH - 50, 15, text="Lives: 3", fill="white", font=("Arial", 12)
        )

        self.paddle = self.canvas.create_rectangle(
            (WIDTH - PADDLE_WIDTH) // 2,
            HEIGHT - 40,
            (WIDTH + PADDLE_WIDTH) // 2,
            HEIGHT - 40 + PADDLE_HEIGHT,
            fill="white",
        )

        self.ball = self.canvas.create_oval(
            WIDTH // 2 - BALL_SIZE // 2,
            HEIGHT // 2,
            WIDTH // 2 + BALL_SIZE // 2,
            HEIGHT // 2 + BALL_SIZE,
            fill="yellow",
        )
        self.ball_dx = random.choice([-4, -3, 3, 4])
        self.ball_dy = -4

        self.bricks = {}
        self.create_bricks()

        self.root.bind("<Motion>", self.move_paddle)
        self.root.bind("<Left>", lambda e: self.move_paddle_key(-30))
        self.root.bind("<Right>", lambda e: self.move_paddle_key(30))
        self.root.bind("<space>", self.toggle_start)
        self.root.bind("<r>", self.restart)
        self.root.bind("<R>", self.restart)

        self.info_text = self.canvas.create_text(
            WIDTH // 2,
            HEIGHT // 2 + 60,
            text="스페이스바를 눌러 시작하세요",
            fill="white",
            font=("Arial", 14),
        )

        self.update()

    def create_bricks(self):
        for row in range(BRICK_ROWS):
            for col in range(BRICK_COLS):
                x1 = col * BRICK_WIDTH + 2
                y1 = row * BRICK_HEIGHT + 40
                x2 = x1 + BRICK_WIDTH - 4
                y2 = y1 + BRICK_HEIGHT - 4
                brick = self.canvas.create_rectangle(
                    x1, y1, x2, y2, fill=BRICK_COLORS[row % len(BRICK_COLORS)], outline="black"
                )
                self.bricks[brick] = True

    def move_paddle(self, event):
        if self.game_over:
            return
        x1, y1, x2, y2 = self.canvas.coords(self.paddle)
        width = x2 - x1
        new_x1 = max(0, min(event.x - width / 2, WIDTH - width))
        self.canvas.coords(self.paddle, new_x1, y1, new_x1 + width, y2)

    def move_paddle_key(self, dx):
        if self.game_over:
            return
        x1, y1, x2, y2 = self.canvas.coords(self.paddle)
        if x1 + dx < 0:
            dx = -x1
        if x2 + dx > WIDTH:
            dx = WIDTH - x2
        self.canvas.move(self.paddle, dx, 0)

    def toggle_start(self, event=None):
        if self.game_over:
            return
        self.running = not self.running
        if self.running:
            self.canvas.itemconfig(self.info_text, text="")
        else:
            self.canvas.itemconfig(self.info_text, text="일시정지 (스페이스바)")

    def restart(self, event=None):
        self.canvas.delete("all")
        self.score = 0
        self.lives = 3
        self.running = False
        self.game_over = False

        self.score_text = self.canvas.create_text(
            50, 15, text="Score: 0", fill="white", font=("Arial", 12)
        )
        self.lives_text = self.canvas.create_text(
            WIDTH - 50, 15, text="Lives: 3", fill="white", font=("Arial", 12)
        )
        self.paddle = self.canvas.create_rectangle(
            (WIDTH - PADDLE_WIDTH) // 2,
            HEIGHT - 40,
            (WIDTH + PADDLE_WIDTH) // 2,
            HEIGHT - 40 + PADDLE_HEIGHT,
            fill="white",
        )
        self.ball = self.canvas.create_oval(
            WIDTH // 2 - BALL_SIZE // 2,
            HEIGHT // 2,
            WIDTH // 2 + BALL_SIZE // 2,
            HEIGHT // 2 + BALL_SIZE,
            fill="yellow",
        )
        self.ball_dx = random.choice([-4, -3, 3, 4])
        self.ball_dy = -4
        self.bricks = {}
        self.create_bricks()
        self.info_text = self.canvas.create_text(
            WIDTH // 2,
            HEIGHT // 2 + 60,
            text="스페이스바를 눌러 시작하세요",
            fill="white",
            font=("Arial", 14),
        )

    def update(self):
        if self.running and not self.game_over:
            self.move_ball()
        self.root.after(16, self.update)

    def move_ball(self):
        self.canvas.move(self.ball, self.ball_dx, self.ball_dy)
        bx1, by1, bx2, by2 = self.canvas.coords(self.ball)

        if bx1 <= 0 or bx2 >= WIDTH:
            self.ball_dx = -self.ball_dx
        if by1 <= 0:
            self.ball_dy = -self.ball_dy

        if by2 >= HEIGHT:
            self.lives -= 1
            self.canvas.itemconfig(self.lives_text, text=f"Lives: {self.lives}")
            if self.lives <= 0:
                self.end_game(False)
                return
            else:
                self.reset_ball()
                self.running = False
                self.canvas.itemconfig(self.info_text, text="스페이스바를 눌러 계속하세요")
                return

        px1, py1, px2, py2 = self.canvas.coords(self.paddle)
        if bx2 >= px1 and bx1 <= px2 and by2 >= py1 and by1 <= py2 and self.ball_dy > 0:
            hit_pos = ((bx1 + bx2) / 2 - px1) / (px2 - px1)
            self.ball_dx = 8 * (hit_pos - 0.5)
            if self.ball_dx == 0:
                self.ball_dx = 0.5
            self.ball_dy = -abs(self.ball_dy)

        hit_brick = None
        for brick in list(self.bricks.keys()):
            rx1, ry1, rx2, ry2 = self.canvas.coords(brick)
            if bx2 >= rx1 and bx1 <= rx2 and by2 >= ry1 and by1 <= ry2:
                hit_brick = brick
                break

        if hit_brick is not None:
            rx1, ry1, rx2, ry2 = self.canvas.coords(hit_brick)
            self.canvas.delete(hit_brick)
            del self.bricks[hit_brick]
            self.score += 10
            self.canvas.itemconfig(self.score_text, text=f"Score: {self.score}")

            overlap_left = bx2 - rx1
            overlap_right = rx2 - bx1
            overlap_top = by2 - ry1
            overlap_bottom = ry2 - by1
            min_overlap = min(overlap_left, overlap_right, overlap_top, overlap_bottom)
            if min_overlap in (overlap_left, overlap_right):
                self.ball_dx = -self.ball_dx
            else:
                self.ball_dy = -self.ball_dy

            if not self.bricks:
                self.end_game(True)

    def reset_ball(self):
        self.canvas.coords(
            self.ball,
            WIDTH // 2 - BALL_SIZE // 2,
            HEIGHT // 2,
            WIDTH // 2 + BALL_SIZE // 2,
            HEIGHT // 2 + BALL_SIZE,
        )
        self.ball_dx = random.choice([-4, -3, 3, 4])
        self.ball_dy = -4
        x1, y1, x2, y2 = self.canvas.coords(self.paddle)
        width = x2 - x1
        new_x1 = (WIDTH - width) / 2
        self.canvas.coords(self.paddle, new_x1, y1, new_x1 + width, y2)

    def end_game(self, won):
        self.running = False
        self.game_over = True
        message = "승리! 축하합니다!" if won else "게임 오버"
        self.canvas.itemconfig(
            self.info_text, text=f"{message}  (R을 눌러 재시작)"
        )


if __name__ == "__main__":
    root = tk.Tk()
    game = Breakout(root)
    root.mainloop()
