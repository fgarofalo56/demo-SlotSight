"""Catalog of fictional floor content for the synthetic generator.

⚠  EVERYTHING IN THIS FILE IS INVENTED. The casino, the game titles, and the
   manufacturers do not exist and are not references to real products. See
   NOTICE.md.

The numbers are, however, *plausible*: denominations, par hold ranges, and
coin-in magnitudes are set to the rough shape of a real regional casino floor
so the analytics produce believable-looking results.
"""

from __future__ import annotations

from dataclasses import dataclass

# ═══════════════════════════════════════════════════════════════════════════
# Floor geography
# ═══════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class ZoneSpec:
    code: str
    name: str
    description: str
    is_high_limit: bool
    share: float  # fraction of total machine count
    traffic: float  # relative coin-in multiplier


ZONES: tuple[ZoneSpec, ...] = (
    ZoneSpec(
        "HL",
        "High Limit Salon",
        "Private salon, $5-$25 denominations, hosted service.",
        True,
        0.06,
        1.00,
    ),
    ZoneSpec(
        "MFN",
        "Main Floor North",
        "Highest-traffic bank rows nearest the hotel lobby entrance.",
        False,
        0.26,
        1.18,
    ),
    ZoneSpec(
        "MFS",
        "Main Floor South",
        "Rows toward the event center; heavy on weekend event nights.",
        False,
        0.24,
        0.94,
    ),
    ZoneSpec(
        "PROM",
        "The Promenade",
        "Walkway banks between the restaurants and the sportsbook.",
        False,
        0.18,
        1.06,
    ),
    ZoneSpec(
        "BAR",
        "Sunset Bar Tops",
        "Embedded bar-top units; lower coin-in, long dwell, high margin.",
        False,
        0.14,
        0.95,
    ),
    ZoneSpec(
        "NSM",
        "Non-Smoking Pavilion",
        "Enclosed non-smoking room; loyal, older, steady play.",
        False,
        0.12,
        0.88,
    ),
)

# ═══════════════════════════════════════════════════════════════════════════
# Fictional manufacturers and cabinets
# ═══════════════════════════════════════════════════════════════════════════

MANUFACTURERS: tuple[str, ...] = (
    "Meridian Gaming",
    "Kestrel Interactive",
    "Halcyon Slots",
    "Bright Harbor Gaming",
    "Vantage Play",
    "Orinoco Games",
)

CABINETS: dict[str, tuple[str, ...]] = {
    "Meridian Gaming": ("Meridian Arc 49", "Meridian Obelisk", "Meridian Flatline"),
    "Kestrel Interactive": ("Kestrel Vista Dual", "Kestrel Spire", "Kestrel Perch"),
    "Halcyon Slots": ("Halcyon Crown 43", "Halcyon Panorama", "Halcyon Bartop"),
    "Bright Harbor Gaming": ("Bright Harbor Lumen", "Bright Harbor Beacon"),
    "Vantage Play": ("Vantage Tower X", "Vantage Slimline"),
    "Orinoco Games": ("Orinoco Curve", "Orinoco Classic Upright"),
}

# ═══════════════════════════════════════════════════════════════════════════
# Fictional game titles
#
# popularity: relative draw. 1.00 is an average earner for its segment.
# ═══════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class TitleSpec:
    name: str
    manufacturer: str
    game_type: str
    popularity: float


TITLES: tuple[TitleSpec, ...] = (
    # ── Strong performers ──────────────────────────────────────────────────
    TitleSpec("Gilded Lagoon", "Meridian Gaming", "video_reel", 1.15),
    TitleSpec("Thunder Peak", "Kestrel Interactive", "video_reel", 1.13),
    TitleSpec("Sapphire Stampede", "Halcyon Slots", "video_reel", 1.12),
    TitleSpec("Starlight Bazaar", "Meridian Gaming", "video_reel", 1.10),
    TitleSpec("Lunar Koi", "Bright Harbor Gaming", "video_reel", 1.09),
    TitleSpec("Golden Aviary", "Vantage Play", "video_reel", 1.07),
    # ── The planted decliner (see scenarios.py) ────────────────────────────
    # Deliberately set HIGH, not low. The story is "this bank used to earn its
    # floor space and has quietly faded" - which is both the more realistic
    # case and the harder one to detect. A title that was always bad is
    # trivial to find; one that decays out from under you is not. Its low
    # index comes entirely from the planted decay, never from its baseline.
    TitleSpec("Sunset Serpent", "Orinoco Games", "video_reel", 1.11),
    # ── Solid middle ───────────────────────────────────────────────────────
    TitleSpec("Emerald Tide", "Kestrel Interactive", "video_reel", 1.05),
    TitleSpec("Crimson Lantern", "Halcyon Slots", "video_reel", 1.03),
    TitleSpec("Jade Monsoon", "Meridian Gaming", "video_reel", 1.02),
    TitleSpec("Copper Canyon Cash", "Orinoco Games", "video_reel", 1.01),
    TitleSpec("Prism Palms", "Bright Harbor Gaming", "video_reel", 1.00),
    TitleSpec("Amber Oasis", "Vantage Play", "video_reel", 0.99),
    TitleSpec("Ruby Rapids", "Kestrel Interactive", "video_reel", 0.98),
    TitleSpec("Cascade Kings", "Halcyon Slots", "video_reel", 0.97),
    TitleSpec("Zephyr Zone", "Orinoco Games", "video_reel", 0.96),
    TitleSpec("Nightbloom", "Meridian Gaming", "video_reel", 0.95),
    # ── Weak tail ──────────────────────────────────────────────────────────
    TitleSpec("Vermilion Vault", "Vantage Play", "video_reel", 0.93),
    TitleSpec("Marigold Mine", "Orinoco Games", "video_reel", 0.91),
    TitleSpec("Bronze Bazaar", "Bright Harbor Gaming", "video_reel", 0.90),
    # ── Mechanical reels: older demographic, steady, lower coin-in ─────────
    TitleSpec("Midnight Mesa", "Orinoco Games", "mechanical_reel", 1.04),
    TitleSpec("Velvet Rhino", "Halcyon Slots", "mechanical_reel", 0.99),
    TitleSpec("Ivory Tusk", "Orinoco Games", "mechanical_reel", 0.94),
    TitleSpec("Obsidian Crown", "Meridian Gaming", "mechanical_reel", 1.06),
    # ── Video poker: very high coin-in, very low hold ──────────────────────
    TitleSpec("Frostfire Kingdom", "Kestrel Interactive", "video_poker", 1.05),
    TitleSpec("Tidal Titan", "Vantage Play", "video_poker", 1.00),
    TitleSpec("Solar Flare Fortune", "Bright Harbor Gaming", "video_poker", 0.96),
    # ── Multigame / keno ───────────────────────────────────────────────────
    TitleSpec("Cobalt Comet", "Meridian Gaming", "keno_multigame", 1.01),
    TitleSpec("Wild Meridian", "Meridian Gaming", "keno_multigame", 0.98),
)

# Titles reserved for planted scenarios - never assigned by random selection.
#
# "Sunset Serpent" exists on exactly one bank. If random placement also put it
# in a healthy zone it would surface as a TOP performer elsewhere on the floor
# while the planted bank was being recommended for conversion. That is a real
# and interesting analytical situation - the same title thriving in one zone
# and dying in another points at floor position rather than the game - but it
# is a *different* lesson than the one this dataset is built to teach, and
# having both at once makes neither land.
RESERVED_TITLES: frozenset[str] = frozenset({"Sunset Serpent"})

# Titles that exist only in the market feed — not on our floor.
# This is what makes a conversion *recommendation* possible.
MARKET_ONLY_TITLES: tuple[TitleSpec, ...] = (
    TitleSpec("Neon Tiki Riches", "Kestrel Interactive", "video_reel", 1.31),
    TitleSpec("Harbor Lights Deluxe", "Meridian Gaming", "video_reel", 1.14),
    TitleSpec("Painted Pony Payday", "Halcyon Slots", "mechanical_reel", 1.08),
)

# ═══════════════════════════════════════════════════════════════════════════
# Denomination economics
#
# base_coin_in_usd  — average daily coin-in for an average unit
# par_hold_range    — theoretical hold the paytable is set to
# weight            — share of the non-high-limit floor
# ═══════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class DenomSpec:
    cents: int
    label: str
    base_coin_in_usd: float
    par_hold_min: float
    par_hold_max: float
    weight: float
    high_limit_only: bool = False


DENOMINATIONS: tuple[DenomSpec, ...] = (
    DenomSpec(1, "Penny", 2_450.0, 0.0825, 0.1180, 0.62),
    DenomSpec(5, "Nickel", 2_100.0, 0.0700, 0.0950, 0.06),
    DenomSpec(25, "Quarter", 3_150.0, 0.0600, 0.0820, 0.16),
    DenomSpec(100, "Dollar", 4_900.0, 0.0480, 0.0680, 0.16),
    DenomSpec(500, "Five Dollar", 16_800.0, 0.0380, 0.0520, 0.0, high_limit_only=True),
    DenomSpec(2500, "Twenty-Five Dollar", 41_000.0, 0.0300, 0.0430, 0.0, high_limit_only=True),
)

# What the High Limit salon actually carries, and in what proportion.
#
# Note the deliberate inclusion of $1. A real high-limit room is not purely
# $5-and-up, and modeling it that way would make the zone impossible to
# benchmark: if a denomination exists ONLY inside one zone, then that zone's
# peer group is itself, its peer index is 1.000 by definition, and you can
# never tell whether it is performing well. Sharing the $1 tier with the main
# floor is what gives High Limit a cross-floor cohort to be measured against.
HIGH_LIMIT_DENOM_WEIGHTS: dict[int, float] = {100: 0.26, 500: 0.54, 2500: 0.20}

# Video poker runs far more coin-in at far lower hold than reels.
GAME_TYPE_MODIFIERS: dict[str, tuple[float, float]] = {
    # game_type: (coin_in_multiplier, par_hold_multiplier)
    "video_reel": (1.00, 1.00),
    "mechanical_reel": (0.78, 0.94),
    "video_poker": (2.35, 0.34),
    "keno_multigame": (0.86, 1.08),
}

# Day-of-week coin-in multipliers. Monday=0 … Sunday=6.
DAY_OF_WEEK_MULTIPLIER: tuple[float, ...] = (
    0.74,  # Mon
    0.71,  # Tue
    0.79,  # Wed
    0.88,  # Thu
    1.34,  # Fri
    1.52,  # Sat
    1.02,  # Sun
)

# ═══════════════════════════════════════════════════════════════════════════
# Fictional external providers and competitors  —  SYNTHETIC. See NOTICE.md.
# ═══════════════════════════════════════════════════════════════════════════

MARKET_PROVIDERS: tuple[str, ...] = ("ReelIndex", "FloorMetrics", "GamingWire")

COMPETITOR_PROPERTIES: tuple[tuple[str, str], ...] = (
    ("Silver Bison Casino", "Regional North"),
    ("Copper Kettle Resort", "Regional North"),
    ("Lantern Bay Casino", "Regional East"),
    ("Wildhorse Junction", "Regional West"),
)

PROMO_NOTES: tuple[str, ...] = (
    "Double points Tuesdays on this bank",
    "$50 free play with new-member signup",
    "Featured in weekend tournament rotation",
    "Bank relocated to main entrance in Q3",
    "Progressive linked across property",
    "",
    "",
)
