import os
import sys
import gc
import json
import math
import random

import fetch
import hints
import machine
import missing_details
import wifi
from pairing import Pairing
from badgeware import State
from badgeware import link as badgelink

try:
    import secrets
except ImportError:
    secrets = None

APP_DIR = "/system/apps/arcelormittal"
try:
    os.chdir(APP_DIR)
    if APP_DIR not in sys.path:
        sys.path.insert(0, APP_DIR)
except OSError:
    pass

badge.mode(HIRES | VSYNC)
screen.antialias = image.X2

# ArcelorMittal Brand Palette
am_orange = color.rgb(255, 55, 0)
am_orange_soft = color.rgb(255, 110, 40)
am_amber = color.rgb(255, 165, 50)
am_red = color.rgb(210, 35, 20)
white = color.rgb(245, 247, 250)
dim_white = color.rgb(245, 247, 250, 155)
faint_white = color.rgb(245, 247, 250, 65)
charcoal = color.rgb(28, 32, 38, 225)
charcoal_border = color.rgb(255, 85, 25, 160)
spinner_col = color.rgb(255, 75, 20, 90)
black = color.rgb(10, 12, 15)

title_font = font.ignore
body_font = missing_details.mona_sans()

WIDTH = 320
HEIGHT = 240
HANDLE_SIZE = 24
NAME_SIZE = 15
VALUE_SIZE = 26
LABEL_SIZE = 13
BODY_SIZE = 14
HINT_SIZE = 13

BUTTON_X = {BUTTON_LEFT: 80, BUTTON_RIGHT: 160, BUTTON_SELECT: 240}
HINT_STYLE = hints.Style(white, dim_white, black)
HINT_RADIUS = 4

CONTRIB_URL = "https://github.com/{user}.contribs"
USER_AVATAR = "https://wsrv.nl/?url=https://github.com/{user}.png&w=150&output=png"
DETAILS_URL = "https://api.github.com/users/{user}"

CACHE_DIR = "/state"
USER_FILE = f"{CACHE_DIR}/am_badge_user.json"
CONTRIB_FILE = f"{CACHE_DIR}/am_badge_contribs.json"
AVATAR_FILE = f"{CACHE_DIR}/am_badge_avatar.png"
CUSTOM_AVATAR = f"{APP_DIR}/assets/profile.png"

GAME = "contacts"
STATE_KEY = "contacts"
OFFER_MS = 15000
SWAP_MS = 8000
DONE_MS = 2500
RETRY_MS = 30000

HEADERS = {"User-Agent": "GitHub Universe Badge 2026"}
TOKEN = str(getattr(secrets, "GITHUB_TOKEN", "") or "").strip()

fetch.AsyncFetch.MAX_HEADER_BYTES = 8192

GRAPH_WEEKS = 53
GRAPH_DAYS = 7
TILE_SIZE = 33
TILE_STEP = 37
GRAPH_TOP = (240 - GRAPH_DAYS * TILE_STEP) // 2
PARALLAX_SHIFT = 8
AVATAR_SIZE = 130
AVATAR_X = 10
AVATAR_Y = 66

try:
    os.mkdir(CACHE_DIR)
except OSError:
    pass


def headers_for(url):
    if TOKEN and url.startswith("https://api.github.com/"):
        headers = dict(HEADERS)
        headers["Authorization"] = "Bearer " + TOKEN
        return headers
    return HEADERS


def setting(key, default=""):
    val = str(getattr(secrets, key, "") or "").strip()
    return val if val else default


def linkedin_url(value):
    value = value.strip()
    if not value:
        return ""
    rest = value.split("://", 1)[-1]
    host, _, path = rest.partition("/")
    host = host.lower()
    if host == "linkedin.com" or host.endswith(".linkedin.com"):
        return "https://" + host + "/" + path.rstrip("/")
    if "." in value:
        return "https://" + rest.rstrip("/")
    return "https://www.linkedin.com/in/" + value.strip("/")


def linkedin_short(url):
    if not url:
        return ""
    handle = url.split("linkedin.com/")[-1].strip("/")
    return handle[3:] if handle.startswith("in/") else handle


def github_url(username):
    return "https://github.com/" + username if username else ""


class Tilt:
    GRAVITY = 16384.0
    SMOOTH_MS = 120
    RECENTRE_MS = 2800

    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.rest_z = None
        self.last_ticks = None

    def update(self):
        ax, _, az = badge.imu()[:3]
        now = badge.ticks
        dt = min(now - self.last_ticks, 200) if self.last_ticks is not None else 0
        self.last_ticks = now
        smooth = 1 - math.exp(-dt / self.SMOOTH_MS)
        recentre = 1 - math.exp(-dt / self.RECENTRE_MS)
        if self.rest_z is None:
            self.rest_z = az
        self.rest_z += (az - self.rest_z) * recentre
        target_x = max(-1.0, min(1.0, -ax / self.GRAVITY * 2))
        target_y = max(-1.0, min(1.0, (az - self.rest_z) / self.GRAVITY * 2))
        self.x += (target_x - self.x) * smooth
        self.y += (target_y - self.y) * smooth


tilt = Tilt()


def draw_am_swoosh(cx, cy, scale, ticks):
    """Draw procedural animated ArcelorMittal ribbon swoosh."""
    t = ticks / 1000.0
    # Subtle breathing & shimmer wave along the 3D ribbon arch
    pts_outer = []
    pts_inner = []
    steps = 18
    for i in range(steps + 1):
        u = i / steps
        angle = math.pi * (0.88 - u * 0.98)
        wave = math.sin(t * 3.2 + u * 4.5) * 1.5 * scale
        rx_out = (26.0 + u * 6.0) * scale
        ry_out = (16.0 - u * 2.0) * scale
        rx_in = (19.0 + u * 4.0) * scale
        ry_in = (10.5 - u * 1.5) * scale

        ox = cx + math.cos(angle) * rx_out - (u - 0.5) * 8.0 * scale
        oy = cy - math.sin(angle) * ry_out + wave
        ix = cx + math.cos(angle) * rx_in - (u - 0.5) * 5.0 * scale
        iy = cy - math.sin(angle) * (ry_in - 2.5 * scale) + wave * 0.7
        pts_outer.append(vec2(ox, oy))
        pts_inner.append(vec2(ix, iy))

    poly = pts_outer + list(reversed(pts_inner))
    pulse = int((math.sin(t * 4.0) * 0.5 + 0.5) * 45)
    screen.pen = color.rgb(255, 45 + pulse, 0)
    screen.shape(shape.custom(poly))

    # Secondary lower ribbon tail (iconic ArcelorMittal loop)
    tail_pts = [
        vec2(cx - 24 * scale, cy + 2 * scale),
        vec2(cx - 4 * scale, cy + 7 * scale + math.sin(t * 3.2) * 1.2 * scale),
        vec2(cx + 22 * scale, cy + 3 * scale),
        vec2(cx + 4 * scale, cy + 11 * scale + math.sin(t * 3.2) * 1.2 * scale),
    ]
    screen.pen = color.rgb(220, 35, 10)
    screen.shape(shape.custom(tail_pts))

    # Travelling highlight spark along the arch
    spark_u = (t * 0.45) % 1.0
    spark_idx = min(steps, int(spark_u * steps))
    spark_pt = pts_outer[spark_idx]
    screen.pen = color.rgb(255, 210, 120, 200)
    screen.circle(vec2(spark_pt.x, spark_pt.y + 2 * scale), max(1, int(2.2 * scale)))


class Download:
    def __init__(self, url, file, force_update):
        self.file = file
        self.temp_file = file + ".tmp"
        self.request = None
        if force_update or not file_exists(file):
            self.request = fetch.url(url, headers=headers_for(url)).to(self.temp_file)

    def ready(self):
        if self.request is None:
            return True
        if self.request:
            if file_exists(self.temp_file):
                try:
                    os.remove(self.file)
                except OSError:
                    pass
                os.rename(self.temp_file, self.file)
            self.request = None
            return True
        return False

    @property
    def state(self):
        return None if self.request is None else self.request.state

    @property
    def error(self):
        return None if self.request is None else self.request.error


class UserProfile:
    # ArcelorMittal heat-steel contribution levels
    levels = [
        color.rgb(18, 16, 20),
        color.rgb(65, 24, 14),
        color.rgb(130, 38, 14),
        color.rgb(205, 52, 12),
        color.rgb(255, 85, 15),
    ]

    def __init__(self, handle, fallback_name):
        self.handle = handle
        self.fallback_name = fallback_name
        self.tile = shape.rounded_rectangle(0, 0, TILE_SIZE, TILE_SIZE, 4)
        self.update()

    def update(self, force_update=False):
        self.name = self.fallback_name or None
        self.company = "@arcelormittal-digital"
        self.followers = None
        self.contribs = None
        self.contribution_data = None
        self.repos = None
        self.avatar = None
        self._download = None
        self._force_update = force_update
        self._error = None
        self._retry_at = 0
        self.missing = []

        if file_exists(CUSTOM_AVATAR):
            try:
                self.avatar = image.load(CUSTOM_AVATAR)
            except Exception:
                self.avatar = None

    def load_user_data(self):
        with open(USER_FILE, "r") as f:
            data = json.load(f)
        if self.handle and data.get("login", "").lower() != self.handle.lower():
            self.update(True)
            return
        self.name = self.fallback_name or data.get("name") or data.get("login") or self.handle
        self.handle = data.get("login") or self.handle
        if data.get("company"):
            self.company = str(data["company"]).strip()
        self.followers = data.get("followers", 0)
        self.repos = data.get("public_repos", 0)
        del data
        gc.collect()

    def load_contrib_data(self):
        with open(CONTRIB_FILE, "r") as f:
            data = json.load(f)
        self.contribs = data.get("total_contributions", 0)
        self.contribution_data = [[0 for _ in range(GRAPH_WEEKS)] for _ in range(GRAPH_DAYS)]
        for week_index, week in enumerate(data.get("weeks", [])[:GRAPH_WEEKS]):
            for day, contribution in enumerate(week.get("contribution_days", [])[:GRAPH_DAYS]):
                self.contribution_data[day][week_index] = contribution.get("level", 0)
        del data
        gc.collect()

    def load_avatar(self):
        if self.avatar is None:
            self.avatar = image.load(AVATAR_FILE)

    def next_download(self):
        if not self.handle:
            return None
        if self.followers is None:
            return "fetching user data...", DETAILS_URL, USER_FILE, self.load_user_data
        if self.contribs is None:
            return "fetching contribs...", CONTRIB_URL, CONTRIB_FILE, self.load_contrib_data
        if self.avatar is None:
            return "fetching avatar...", USER_AVATAR, AVATAR_FILE, self.load_avatar
        return None

    def fail(self, error):
        self._error = error
        self._retry_at = badge.ticks + RETRY_MS
        self._download = None

    def fetch_step(self):
        if self._error:
            if badge.ticks < self._retry_at:
                return "offline cache mode"
            self._error = None

        pending = self.next_download()
        if pending is None:
            return None

        label, url, file, load = pending

        if self._download is None or self._download.file != file:
            if self._force_update or not file_exists(file):
                self.missing = missing_details.missing("WIFI_SSID")
                if self.missing:
                    return None
            self._download = Download(url.format(user=self.handle), file, self._force_update)

        if self._download.ready():
            self._download = None
            try:
                load()
            except (OSError, ValueError, KeyError) as e:
                try:
                    os.remove(file)
                except OSError:
                    pass
                self.fail(e)
            return label

        if self._download.error:
            self.fail(self._download.error)
            return label

        return self._download.state if self._download.state not in ("Idle", "Fetching") else label

    def draw_graph(self):
        graph_width = GRAPH_WEEKS * TILE_STEP
        travel = (graph_width - screen.width) / 2
        offset_x = int(-math.sin(badge.ticks / 5000) * travel + travel + tilt.x * PARALLAX_SHIFT)
        offset_y = GRAPH_TOP - int(tilt.y * PARALLAX_SHIFT)

        for y in range(GRAPH_DAYS):
            for x in range(GRAPH_WEEKS):
                pos_x = x * TILE_STEP - offset_x
                if pos_x + TILE_SIZE < 0 or pos_x > screen.width:
                    continue
                level = self.contribution_data[y][x] if self.contribution_data else ((x + y) % 3)
                screen.pen = UserProfile.levels[min(level, len(UserProfile.levels) - 1)]
                self.tile.transform = mat3().translate(pos_x, y * TILE_STEP + offset_y)
                screen.shape(self.tile)

    def draw_avatar(self, badge_id):
        # Branded orange frame around avatar
        screen.pen = am_orange
        screen.shape(shape.rounded_rectangle(AVATAR_X - 2, AVATAR_Y - 2, AVATAR_SIZE + 4, AVATAR_SIZE + 4, 8))
        if self.avatar:
            screen.blit(self.avatar, rect(AVATAR_X, AVATAR_Y, AVATAR_SIZE, AVATAR_SIZE))
            return
        if file_exists(AVATAR_FILE):
            try:
                self.avatar = image.load(AVATAR_FILE)
                screen.blit(self.avatar, rect(AVATAR_X, AVATAR_Y, AVATAR_SIZE, AVATAR_SIZE))
                return
            except Exception:
                pass
        badgelink.draw_identicon(screen, badge_id, AVATAR_X, AVATAR_Y, AVATAR_SIZE)


def measure(text, size=None):
    return screen.measure_text(text, font_size=size) if size else screen.measure_text(text)


def fit(text, width, size=None):
    while text and measure(text, size)[0] > width:
        text = text[:-1]
    return text


def write(text, x, y, size=None):
    if size:
        screen.text(text, x, y, size)
    else:
        screen.text(text, x, y)


def centred(text, y, typeface, pen, size=None):
    screen.font = typeface
    screen.pen = pen
    text = fit(text, WIDTH - 16, size)
    w, _ = measure(text, size)
    write(text, (WIDTH - w) / 2, y, size)


def draw_hint(label, shape_btns, left):
    screen.font = body_font
    label_width, _ = measure(label, HINT_SIZE)
    dots_width = hints.hint_width(shape_btns, HINT_RADIUS)
    hints.draw_hint(HINT_STYLE, shape_btns, shape_btns, left + dots_width / 2, 224, HINT_RADIUS)
    screen.pen = dim_white
    write(label, left + dots_width + 6, 216, HINT_SIZE)
    return dots_width + 6 + label_width


def hint_size(label, shape_btns):
    screen.font = body_font
    return hints.hint_width(shape_btns, HINT_RADIUS) + 6 + measure(label, HINT_SIZE)[0]


def draw_hints(*pairs):
    right = WIDTH - 8
    for label, shape_btns in pairs:
        right -= hint_size(label, shape_btns)
        draw_hint(label, shape_btns, right)
        right -= 12


def clean_card(value):
    if not isinstance(value, dict):
        return None
    card = {key: str(value.get(key, "")).strip()[:120] for key in ("name", "github", "linkedin")}
    if card["linkedin"] and not card["linkedin"].startswith("https://"):
        card["linkedin"] = ""
    if not card["name"] or not (card["github"] or card["linkedin"]):
        return None
    return card


class Book:
    def __init__(self):
        saved = {"cards": []}
        State.load(STATE_KEY, saved)
        self.cards = []
        for entry in saved["cards"] if isinstance(saved["cards"], list) else []:
            card = clean_card(entry)
            if card is not None:
                card["badge"] = str(entry.get("badge", ""))
                self.cards.append(card)

    def add(self, card, badge_id):
        card = dict(card)
        card["badge"] = badgelink.badge_id_hex(badge_id)
        self.cards = [existing for existing in self.cards if existing["badge"] != card["badge"]]
        self.cards.insert(0, card)
        State.save(STATE_KEY, {"cards": self.cards})


class Swap:
    def __init__(self, card, partner_id):
        self.partner_id = partner_id
        self.outgoing = json.dumps(card).encode()
        self.chunks = None
        self.sent = 0
        self.parts = {}
        self.total = None
        self.card = None
        self.acked = False

    def pump(self, link):
        if self.chunks is None:
            size = max(1, link.capacity() - 3)
            self.chunks = [self.outgoing[index:index + size] for index in range(0, len(self.outgoing), size)]
        while self.sent < len(self.chunks):
            chunk = b"C" + bytes((self.sent, len(self.chunks))) + self.chunks[self.sent]
            if not link.send(chunk):
                return
            self.sent += 1

    def receive(self, message, link):
        kind = message[:1]
        if kind == b"K":
            self.acked = True
        elif kind == b"C" and len(message) >= 3 and self.card is None:
            self.total = message[2]
            self.parts[message[1]] = message[3:]
            if len(self.parts) == self.total:
                try:
                    card = clean_card(json.loads(b"".join(self.parts[index] for index in range(self.total))))
                except (KeyError, ValueError):
                    card = None
                if card is not None:
                    self.card = card
                    link.send(b"K")

    @property
    def done(self):
        return self.card is not None and self.acked


class ArcelorMittalApp:
    BADGE = 0
    QR = 1
    OFFER = 2
    SWAP = 3
    DONE = 4

    PANEL_COMPANY = 0
    PANEL_STATS = 1

    def __init__(self):
        self.handle = setting("AM_GITHUB_USERNAME", "mgliot")
        self.contact_name = setting("CONTACT_NAME", "Marcelino Gonzalez")
        self.linkedin_raw = setting("CONTACT_LINKEDIN", "www.linkedin.com/in/marcelino-gonzalez-lozano-pmp")
        self.linkedin = linkedin_url(self.linkedin_raw)
        self.linkedin_slug = linkedin_short(self.linkedin)

        self.user = UserProfile(self.handle, self.contact_name)
        self.link = badgelink.Link(GAME)
        self.proximity = badgelink.Proximity(self.link)
        self.pairing = Pairing(74, 138, 6)
        self.book = Book()

        self.card = {
            "name": self.contact_name or self.user.name or self.link.name,
            "github": self.handle,
            "linkedin": self.linkedin,
        }
        self.links = []
        if self.linkedin:
            self.links.append(("LinkedIn", self.linkedin))
        if self.handle:
            self.links.append(("GitHub", github_url(self.handle)))

        self.mode = self.BADGE
        self.panel = self.PANEL_COMPANY
        self.mode_at = 0
        self.was_linked = False
        self.my_accept = False
        self.their_accept = False
        self.swap = None
        self.saved = None
        self.message = ""
        self.link_index = 0
        self.qr = None
        self.qr_url = None

    def set_mode(self, mode, now):
        self.mode = mode
        self.mode_at = now

    def part(self, now, message=""):
        partner = self.link.partner
        self.proximity.rest(partner.id if partner else None, now)
        self.link.leave()
        self.swap = None
        self.message = message
        self.set_mode(self.BADGE, now)

    def update(self, now):
        tilt.update()
        self.link.pump()
        linked = self.link.linked

        if linked and not self.was_linked:
            if self.mode in (self.BADGE, self.QR):
                self.my_accept = False
                self.their_accept = False
                self.message = ""
                self.set_mode(self.OFFER, now)
            else:
                self.link.leave()

        if self.was_linked and not linked and self.mode in (self.OFFER, self.SWAP):
            self.proximity.clear()
            if self.swap is not None and self.swap.card is not None:
                self.finish(now)
            else:
                self.message = "they walked away"
                self.swap = None
                self.set_mode(self.BADGE, now)
        self.was_linked = linked

        if linked:
            for msg in self.link.receive():
                if msg == b"A":
                    self.their_accept = True
                elif msg == b"D":
                    self.part(now, "they said no thanks")
                elif self.swap is not None:
                    self.swap.receive(msg, self.link)

        both_held = badge.held(BUTTON_LEFT) and badge.held(BUTTON_RIGHT)
        if self.handle and both_held and (badge.pressed(BUTTON_LEFT) or badge.pressed(BUTTON_RIGHT)):
            self.user.update(True)

        self.status = self.user.fetch_step()

        if self.mode == self.BADGE:
            if self.links:
                self.proximity.update(now)
            if badge.pressed(BUTTON_RIGHT) or badge.pressed(BUTTON_LEFT) or badge.pressed(BUTTON_UP) or badge.pressed(BUTTON_DOWN):
                self.panel = self.PANEL_STATS if self.panel == self.PANEL_COMPANY else self.PANEL_COMPANY
            elif badge.pressed(BUTTON_SELECT) and self.links:
                url = self.links[self.link_index][1]
                self.qr = image.qr(url, image.QR_LOW, 2)
                self.qr_url = url
                self.set_mode(self.QR, now)
            elif badge.pressed(BUTTON_BACK):
                reset()

        elif self.mode == self.QR:
            if badge.pressed(BUTTON_RIGHT) or badge.pressed(BUTTON_LEFT):
                if len(self.links) > 1:
                    self.link_index = (self.link_index + 1) % len(self.links)
            elif badge.pressed(BUTTON_SELECT) or badge.pressed(BUTTON_BACK):
                self.set_mode(self.BADGE, now)
                return
            url = self.links[self.link_index][1]
            if url != self.qr_url:
                self.qr = image.qr(url, image.QR_LOW, 2)
                self.qr_url = url

        elif self.mode == self.OFFER:
            if badge.pressed(BUTTON_SELECT) and not self.my_accept:
                self.my_accept = True
                self.swap = Swap(self.card, self.link.partner.id)
                self.link.send(b"A")
            elif badge.pressed(BUTTON_LEFT) or badge.pressed(BUTTON_BACK):
                self.link.send(b"D")
                self.part(now)
                return
            if self.my_accept and self.their_accept:
                self.set_mode(self.SWAP, now)
            elif now - self.mode_at > OFFER_MS:
                self.link.send(b"D")
                self.part(now, "swap timed out")

        elif self.mode == self.SWAP:
            self.swap.pump(self.link)
            if self.swap.done:
                self.finish(now)
            elif now - self.mode_at > SWAP_MS:
                self.part(now, "swap failed, try again")

        elif self.mode == self.DONE:
            if now - self.mode_at > DONE_MS or badge.pressed(BUTTON_SELECT):
                self.set_mode(self.BADGE, now)

        self.link.update()
        lights = self.proximity.lights(now) if self.mode == self.BADGE else None
        badge.caselights(*(lights or (0.5 if self.mode in (self.OFFER, self.SWAP) else 0,)))

    def finish(self, now):
        self.saved = self.swap.card
        self.book.add(self.saved, self.swap.partner_id)
        self.part(now)
        self.set_mode(self.DONE, now)

    def draw_header(self, now):
        # Top dark glass header bar
        screen.pen = charcoal
        screen.rectangle(0, 0, WIDTH, 56)
        screen.pen = am_orange
        screen.rectangle(0, 55, WIDTH, 2)

        # Animated ArcelorMittal logo on top-left
        draw_am_swoosh(32, 22, 0.85, now)
        screen.font = body_font
        screen.pen = white
        write("ArcelorMittal", 64, 6, 17)

        # User full name & handle
        display_name = self.user.name or self.contact_name or self.handle
        screen.pen = am_amber
        write(fit(display_name, WIDTH - 70, 22), 64, 26, 22)

    def draw_company_panel(self, now):
        px, py, pw, ph = 148, 66, 164, 130
        screen.pen = charcoal
        screen.shape(shape.rounded_rectangle(px, py, pw, ph, 8))
        screen.pen = charcoal_border
        screen.shape(shape.rounded_rectangle(px, py, pw, ph, 8).stroke(1.5))

        # Animated signature swoosh inside the company card
        draw_am_swoosh(px + pw - 34, py + 24, 0.9, now)

        screen.font = body_font
        screen.pen = am_orange_soft
        write("ArcelorMittal Digital", px + 10, py + 10, 14)

        screen.pen = white
        write("@" + self.handle, px + 10, py + 32, 18)

        screen.pen = dim_white
        write("LinkedIn:", px + 10, py + 58, 13)
        screen.pen = white
        write(fit(self.linkedin_slug or "marcelino-gonzalez", pw - 20, 14), px + 10, py + 74, 14)

        peer = self.proximity.syncing()
        if peer is not None:
            progress = self.proximity.progress(now)
            screen.pen = am_amber
            write(fit("IR syncing: " + peer.name, pw - 20, 13), px + 10, py + 102, 13)
            screen.pen = faint_white
            screen.rectangle(px + 10, py + 118, pw - 20, 5)
            screen.pen = am_orange
            screen.rectangle(px + 10, py + 118, int((pw - 20) * progress), 5)
        else:
            screen.pen = am_amber
            msg = self.message or (self.status if self.status else "IR Ready · Hold badges")
            write(fit(msg, pw - 20, 12), px + 10, py + 106, 12)

    def draw_stat(self, title, value, x, y):
        screen.font = body_font
        screen.pen = white if value is not None else faint_white
        text = str(value) if value is not None else "-"
        write(text, x, y, 22)
        screen.pen = am_orange_soft
        write(title, x + 68, y + 4, 14)

    def draw_stats_panel(self):
        px, py, pw, ph = 148, 66, 164, 130
        screen.pen = charcoal
        screen.shape(shape.rounded_rectangle(px, py, pw, ph, 8))
        screen.pen = charcoal_border
        screen.shape(shape.rounded_rectangle(px, py, pw, ph, 8).stroke(1.5))

        self.draw_stat("followers", self.user.followers, px + 12, py + 12)
        self.draw_stat("contribs", self.user.contribs, px + 12, py + 52)
        self.draw_stat("repos", self.user.repos, px + 12, py + 92)

    def draw_badge(self, now):
        self.user.draw_graph()
        self.draw_header(now)
        self.user.draw_avatar(self.link.id)

        if self.panel == self.PANEL_COMPANY:
            self.draw_company_panel(now)
            toggle_label = "stats"
        else:
            self.draw_stats_panel()
            toggle_label = "card"

        # Bottom bar
        screen.pen = charcoal
        screen.rectangle(0, 206, WIDTH, 34)
        screen.font = body_font
        screen.pen = am_orange_soft
        write("in/" + fit(self.linkedin_slug, 110, 13), 8, 216, 13)
        draw_hints(("share QR", (BUTTON_SELECT,)), (toggle_label, (BUTTON_RIGHT,)))

    def draw_qr(self, now):
        self.user.draw_graph()
        screen.pen = color.rgb(10, 12, 15, 215)
        screen.rectangle(0, 0, WIDTH, HEIGHT)

        label, url = self.links[self.link_index]
        qr_size = 136
        qx = (WIDTH - qr_size) // 2
        qy = 10

        screen.pen = am_orange
        screen.shape(shape.rounded_rectangle(qx - 6, qy - 6, qr_size + 12, qr_size + 12, 8))
        screen.pen = white
        screen.rectangle(qx - 3, qy - 3, qr_size + 6, qr_size + 6)
        if self.qr is not None:
            screen.blit(self.qr, rect(0, 0, self.qr.width, self.qr.height), rect(qx, qy, qr_size, qr_size))

        draw_am_swoosh(28, 172, 0.7, now)
        centred(f"{self.contact_name} · {label}", 156, body_font, am_amber, 17)
        centred(url.split("://")[-1], 180, body_font, white, 14)

        if len(self.links) > 1:
            draw_hints(("back", (BUTTON_SELECT,)), ("switch", (BUTTON_RIGHT,)))
        else:
            draw_hints(("back", (BUTTON_SELECT,)))

    def draw_partner(self, status, pen):
        partner = self.link.partner
        if partner is None:
            return
        badgelink.draw_identicon(screen, partner.id, (WIDTH - 70) // 2, 24, 70)
        centred(partner.name, 106, title_font, white)
        centred(status, 136, body_font, pen, BODY_SIZE)

    def draw_offer(self, now):
        self.user.draw_graph()
        screen.pen = color.rgb(10, 12, 15, 210)
        screen.rectangle(0, 0, WIDTH, HEIGHT)
        if self.my_accept:
            status = "waiting for them..."
        elif self.their_accept:
            status = "they want to swap cards"
        else:
            status = "swap contact cards?"
        self.draw_partner(status, am_orange if self.their_accept else dim_white)
        remaining = max(0, OFFER_MS - (now - self.mode_at))
        screen.pen = faint_white
        screen.rectangle(16, 170, int((WIDTH - 32) * remaining / OFFER_MS), 4)
        if self.my_accept:
            draw_hints(("cancel", (BUTTON_LEFT,)))
        else:
            draw_hints(("swap", (BUTTON_SELECT,)), ("decline", (BUTTON_LEFT,)))

    def draw_done(self, now):
        self.user.draw_graph()
        screen.pen = color.rgb(10, 12, 15, 210)
        screen.rectangle(0, 0, WIDTH, HEIGHT)
        draw_am_swoosh(WIDTH // 2, 65, 1.3, now)
        centred("Contact Saved!", 100, body_font, am_orange, 20)
        if self.saved:
            centred(self.saved["name"], 130, title_font, white)

    def draw(self, now):
        screen.pen = black
        screen.clear()
        if self.mode == self.BADGE:
            self.draw_badge(now)
        elif self.mode == self.QR:
            self.draw_qr(now)
        elif self.mode == self.OFFER:
            self.draw_offer(now)
        elif self.mode == self.SWAP:
            self.draw_partner("swapping cards...", am_amber)
        elif self.mode == self.DONE:
            self.draw_done(now)


app = ArcelorMittalApp()


def update():
    now = badge.ticks
    app.update(now)
    app.draw(now)


def on_exit():
    badge.caselights(0)
    app.link.close()


run(update)
