"""
뱀 게임 - 사람 vs AI 대결
- 사람 뱀: 방향키(화살표)로 조작
- AI 뱀: 가장 가까운 사과를 향해 자동으로 이동 (충돌 회피)
- 먼저 목표 점수에 도달하거나, 상대가 죽으면 승리
"""

import random
import sys
from collections import deque

import pygame

# ---------- 설정값 ----------
CELL_SIZE = 20
GRID_WIDTH = 30
GRID_HEIGHT = 24
SCREEN_WIDTH = CELL_SIZE * GRID_WIDTH
SCREEN_HEIGHT = CELL_SIZE * GRID_HEIGHT + 60  # 상단에 점수판 영역 추가
FPS = 10
WIN_SCORE = 15
APPLE_COUNT = 3  # 동시에 존재하는 사과 개수

# 색상
BLACK = (15, 15, 15)
WHITE = (240, 240, 240)
RED = (220, 60, 60)
GREEN = (60, 200, 80)
DARK_GREEN = (30, 120, 50)
BLUE = (60, 140, 220)
DARK_BLUE = (30, 70, 130)
GRAY = (60, 60, 60)
YELLOW = (230, 200, 60)

UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)


def random_empty_cell(occupied):
    while True:
        cell = (random.randint(0, GRID_WIDTH - 1), random.randint(0, GRID_HEIGHT - 1))
        if cell not in occupied:
            return cell


class Snake:
    def __init__(self, start_pos, direction, color, dark_color, name):
        self.body = deque([start_pos])
        self.direction = direction
        self.color = color
        self.dark_color = dark_color
        self.name = name
        self.score = 0
        self.alive = True
        self.grow_pending = 2  # 시작 시 길이를 조금 늘려줌

    def head(self):
        return self.body[0]

    def next_head(self, direction=None):
        d = direction if direction else self.direction
        hx, hy = self.head()
        return (hx + d[0], hy + d[1])

    def move(self):
        if not self.alive:
            return
        new_head = self.next_head()
        self.body.appendleft(new_head)
        if self.grow_pending > 0:
            self.grow_pending -= 1
        else:
            self.body.pop()

    def grow(self, amount=1):
        self.grow_pending += amount
        self.score += 1

    def set_direction(self, new_direction):
        # 정반대 방향으로는 즉시 전환할 수 없음 (자기 자신과 정면 충돌 방지)
        if (new_direction[0] * -1, new_direction[1] * -1) == self.direction:
            return
        self.direction = new_direction

    def check_wall_collision(self):
        hx, hy = self.head()
        return hx < 0 or hx >= GRID_WIDTH or hy < 0 or hy >= GRID_HEIGHT

    def check_self_collision(self):
        head = self.head()
        return head in list(self.body)[1:]

    def draw(self, surface, offset_y):
        for i, (x, y) in enumerate(self.body):
            rect = pygame.Rect(x * CELL_SIZE, y * CELL_SIZE + offset_y, CELL_SIZE, CELL_SIZE)
            color = self.color if i == 0 else self.dark_color
            pygame.draw.rect(surface, color, rect)
            pygame.draw.rect(surface, BLACK, rect, 1)


def ai_choose_direction(ai_snake, player_snake, apples):
    """AI가 가장 가까운 사과를 향해 이동할 방향을 결정.
    벽/자기 몸/상대 몸과 충돌하는 방향은 최대한 피한다."""
    head = ai_snake.head()

    # 가장 가까운 사과 찾기 (맨해튼 거리 기준)
    target = min(apples, key=lambda a: abs(a[0] - head[0]) + abs(a[1] - head[1]))

    obstacles = set(list(ai_snake.body)[:-1]) | set(list(player_snake.body))

    candidates = [UP, DOWN, LEFT, RIGHT]
    # 반대 방향(정면 충돌) 제거
    opposite = (ai_snake.direction[0] * -1, ai_snake.direction[1] * -1)
    candidates = [d for d in candidates if d != opposite]

    def is_safe(direction):
        nx, ny = head[0] + direction[0], head[1] + direction[1]
        if nx < 0 or nx >= GRID_WIDTH or ny < 0 or ny >= GRID_HEIGHT:
            return False
        if (nx, ny) in obstacles:
            return False
        return True

    safe_candidates = [d for d in candidates if is_safe(d)]
    if not safe_candidates:
        # 안전한 방향이 없으면 그냥 반대방향이라도 살아있는 쪽으로
        safe_candidates = [d for d in [UP, DOWN, LEFT, RIGHT] if is_safe(d)]
        if not safe_candidates:
            return ai_snake.direction  # 어쩔 수 없음, 그대로 진행 (죽을 수 있음)

    # 목표(사과)와의 거리를 줄이는 방향을 우선 선택
    def score(direction):
        nx, ny = head[0] + direction[0], head[1] + direction[1]
        return abs(target[0] - nx) + abs(target[1] - ny)

    safe_candidates.sort(key=score)
    return safe_candidates[0]


def draw_scoreboard(surface, font, player, ai):
    pygame.draw.rect(surface, GRAY, (0, 0, SCREEN_WIDTH, 60))
    p_text = font.render(f"사람: {player.score}", True, BLUE)
    a_text = font.render(f"AI: {ai.score}", True, RED)
    surface.blit(p_text, (20, 18))
    surface.blit(a_text, (SCREEN_WIDTH - a_text.get_width() - 20, 18))

    goal_text = font.render(f"목표 점수: {WIN_SCORE}", True, WHITE)
    surface.blit(goal_text, (SCREEN_WIDTH // 2 - goal_text.get_width() // 2, 18))


def show_message(surface, font_big, font_small, lines):
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    overlay.set_alpha(200)
    overlay.fill(BLACK)
    surface.blit(overlay, (0, 0))

    total_height = len(lines) * 50
    start_y = SCREEN_HEIGHT // 2 - total_height // 2
    for i, (text, font, color) in enumerate(lines):
        rendered = font.render(text, True, color)
        rect = rendered.get_rect(center=(SCREEN_WIDTH // 2, start_y + i * 50))
        surface.blit(rendered, rect)


def reset_game():
    player = Snake(
        start_pos=(GRID_WIDTH // 4, GRID_HEIGHT // 2),
        direction=RIGHT,
        color=BLUE,
        dark_color=DARK_BLUE,
        name="사람",
    )
    ai = Snake(
        start_pos=(GRID_WIDTH * 3 // 4, GRID_HEIGHT // 2),
        direction=LEFT,
        color=RED,
        dark_color=(150, 40, 40),
        name="AI",
    )

    apples = []
    occupied = set(player.body) | set(ai.body)
    for _ in range(APPLE_COUNT):
        apple = random_empty_cell(occupied | set(apples))
        apples.append(apple)

    return player, ai, apples


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("뱀 게임 - 사람 vs AI")
    clock = pygame.time.Clock()

    try:
        font = pygame.font.SysFont("malgungothic", 24)
        font_big = pygame.font.SysFont("malgungothic", 48, bold=True)
    except Exception:
        font = pygame.font.SysFont(None, 24)
        font_big = pygame.font.SysFont(None, 48, bold=True)

    player, ai, apples = reset_game()
    game_over = False
    winner_text = ""

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                if not game_over:
                    if event.key in (pygame.K_UP, pygame.K_w):
                        player.set_direction(UP)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        player.set_direction(DOWN)
                    elif event.key in (pygame.K_LEFT, pygame.K_a):
                        player.set_direction(LEFT)
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        player.set_direction(RIGHT)
                if event.key == pygame.K_r and game_over:
                    player, ai, apples = reset_game()
                    game_over = False
                    winner_text = ""

        if not game_over:
            # AI 방향 결정
            ai_dir = ai_choose_direction(ai, player, apples)
            ai.set_direction(ai_dir)

            player.move()
            ai.move()

            # 사과 섭취 처리
            for snake in (player, ai):
                if snake.head() in apples:
                    apples.remove(snake.head())
                    snake.grow()
                    occupied = set(player.body) | set(ai.body) | set(apples)
                    apples.append(random_empty_cell(occupied))

            # 충돌 판정
            if player.check_wall_collision() or player.check_self_collision():
                player.alive = False
            if ai.check_wall_collision() or ai.check_self_collision():
                ai.alive = False

            # 서로 부딪힘 (머리끼리 or 머리-몸통)
            if player.alive and player.head() in list(ai.body):
                player.alive = False
            if ai.alive and ai.head() in list(player.body):
                ai.alive = False

            # 게임 종료 조건 판정
            if not player.alive and not ai.alive:
                game_over = True
                winner_text = "무승부! 둘 다 충돌했습니다."
            elif not player.alive:
                game_over = True
                winner_text = "AI 승리! 사람이 충돌했습니다."
            elif not ai.alive:
                game_over = True
                winner_text = "사람 승리! AI가 충돌했습니다."
            elif player.score >= WIN_SCORE:
                game_over = True
                winner_text = "사람 승리! 목표 점수 달성."
            elif ai.score >= WIN_SCORE:
                game_over = True
                winner_text = "AI 승리! 목표 점수 달성."

        # ---------- 그리기 ----------
        screen.fill(BLACK)

        board_offset_y = 60
        board_rect = pygame.Rect(0, board_offset_y, SCREEN_WIDTH, SCREEN_HEIGHT - board_offset_y)
        pygame.draw.rect(screen, (25, 25, 25), board_rect)

        for ax, ay in apples:
            rect = pygame.Rect(ax * CELL_SIZE, ay * CELL_SIZE + board_offset_y, CELL_SIZE, CELL_SIZE)
            pygame.draw.rect(screen, YELLOW, rect)
            pygame.draw.rect(screen, BLACK, rect, 1)

        player.draw(screen, board_offset_y)
        ai.draw(screen, board_offset_y)

        draw_scoreboard(screen, font, player, ai)

        if game_over:
            show_message(
                screen,
                font_big,
                font,
                [
                    (winner_text, font_big, WHITE),
                    ("R 키를 눌러 다시 시작 | ESC로 종료", font, WHITE),
                ],
            )

        pygame.display.flip()
        clock.tick(FPS)


if __name__ == "__main__":
    main()
