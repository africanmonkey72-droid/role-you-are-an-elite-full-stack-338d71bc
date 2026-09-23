from dataclasses import dataclass


@dataclass(frozen=True)
class SportProfile:
    key: str
    label: str
    leagues: tuple[str, ...]
    default_home_mean: float
    default_away_mean: float
    default_home_sd: float
    default_away_sd: float
    default_correlation: float
    markets: tuple[str, ...]
    metrics: tuple[tuple[str, str], ...]


SPORT_PROFILES: dict[str, SportProfile] = {
    "basketball": SportProfile(
        key="basketball",
        label="Basketball",
        leagues=("NBA", "NCAA Basketball"),
        default_home_mean=112.0,
        default_away_mean=108.0,
        default_home_sd=11.0,
        default_away_sd=11.0,
        default_correlation=0.2,
        markets=("moneyline", "spread", "game_total", "team_total", "first_half", "first_quarter", "player_props"),
        metrics=(
            ("offensive_rating", "Offensive rating"),
            ("defensive_rating", "Defensive rating"),
            ("pace", "Pace"),
            ("true_shooting_percentage", "True Shooting %"),
            ("rebound_rate", "Rebound rate"),
            ("turnover_rate", "Turnover rate"),
            ("foul_trouble_risk", "Foul trouble risk"),
            ("interior_efficiency", "Interior efficiency"),
            ("perimeter_efficiency", "Perimeter efficiency"),
            ("positional_matchup_synergy", "Positional matchup synergy"),
            ("back_to_back_rest", "Back-to-back rest"),
            ("travel_distance", "Travel distance"),
            ("altitude", "Altitude"),
        ),
    ),
    "football": SportProfile(
        key="football",
        label="Football",
        leagues=("NFL", "NCAA Football"),
        default_home_mean=24.0,
        default_away_mean=21.0,
        default_home_sd=10.0,
        default_away_sd=10.0,
        default_correlation=0.12,
        markets=("moneyline", "spread", "game_total", "first_half", "first_quarter", "team_total", "player_props"),
        metrics=(
            ("epa_per_play", "EPA per play"),
            ("success_rate", "Success rate"),
            ("third_down_efficiency", "3rd down efficiency"),
            ("red_zone_conversion", "Red-zone conversion"),
            ("pass_rush_win_rate", "Pass-rush win rate"),
            ("pass_protection_win_rate", "Pass-protection win rate"),
            ("quarterback_injury_impact", "Quarterback injury impact"),
            ("offensive_line_injury_impact", "Offensive line injury impact"),
            ("cornerback_injury_impact", "Cornerback injury impact"),
            ("special_teams_efficiency", "Special teams efficiency"),
            ("wind_speed", "Wind speed"),
            ("temperature", "Temperature"),
            ("precipitation", "Precipitation"),
        ),
    ),
    "baseball": SportProfile(
        key="baseball",
        label="Baseball",
        leagues=("MLB",),
        default_home_mean=4.7,
        default_away_mean=4.3,
        default_home_sd=2.8,
        default_away_sd=2.8,
        default_correlation=0.05,
        markets=("moneyline", "run_line", "first_five", "game_total", "pitcher_props", "batter_props"),
        metrics=(
            ("starting_pitcher_xfip", "Starting pitcher xFIP"),
            ("starting_pitcher_siera", "Starting pitcher SIERA"),
            ("pitcher_velocity", "Pitcher velocity"),
            ("pitch_mix", "Pitch mix"),
            ("lineup_woba_vs_lhp", "Lineup wOBA vs LHP"),
            ("lineup_woba_vs_rhp", "Lineup wOBA vs RHP"),
            ("bullpen_fatigue", "Bullpen fatigue"),
            ("park_factor", "Park factor"),
            ("wind_direction", "Wind direction"),
            ("umpire_zone_tendency", "Umpire zone tendency"),
            ("defensive_runs_saved", "Defensive runs saved"),
        ),
    ),
    "hockey": SportProfile(
        key="hockey",
        label="Hockey",
        leagues=("NHL",),
        default_home_mean=3.2,
        default_away_mean=2.9,
        default_home_sd=1.7,
        default_away_sd=1.7,
        default_correlation=0.1,
        markets=("moneyline", "puck_line", "grand_salami", "first_period", "player_props"),
        metrics=(
            ("xg_for", "Expected goals for"),
            ("xg_against", "Expected goals against"),
            ("corsi_percentage", "Corsi %"),
            ("fenwick_percentage", "Fenwick %"),
            ("high_danger_chances", "High-danger chances"),
            ("goaltender_gsax", "Goaltender GSAx"),
            ("power_play_efficiency", "Power-play efficiency"),
            ("penalty_kill_efficiency", "Penalty-kill efficiency"),
            ("faceoff_win_rate", "Faceoff win %"),
            ("line_matching_edge", "Home line-matching edge"),
            ("back_to_back_goalie_risk", "Back-to-back goalie risk"),
        ),
    ),
    "soccer": SportProfile(
        key="soccer",
        label="Soccer",
        leagues=("Premier League", "Champions League", "MLS"),
        default_home_mean=1.55,
        default_away_mean=1.2,
        default_home_sd=1.05,
        default_away_sd=0.95,
        default_correlation=0.08,
        markets=("three_way_moneyline", "draw_no_bet", "btts", "asian_handicap", "goals_total", "anytime_goalscorer"),
        metrics=(
            ("xg", "Expected goals"),
            ("xa", "Expected assists"),
            ("shot_creation_actions", "Shot-creation actions"),
            ("ppda", "Pressing intensity (PPDA)"),
            ("set_piece_efficiency", "Set-piece efficiency"),
            ("rotation_load", "Fixture rotation load"),
            ("travel_context", "Travel context"),
            ("card_suspension_risk", "Card/suspension risk"),
        ),
    ),
    "tennis": SportProfile(
        key="tennis",
        label="Tennis",
        leagues=("ATP", "WTA", "Grand Slam"),
        default_home_mean=2.0,
        default_away_mean=1.0,
        default_home_sd=0.75,
        default_away_sd=0.75,
        default_correlation=0.0,
        markets=("match_winner", "set_betting", "game_handicap", "total_games"),
        metrics=(
            ("first_serve_win_rate", "1st serve win %"),
            ("second_serve_win_rate", "2nd serve win %"),
            ("break_point_conversion", "Break point conversion"),
            ("surface_split", "Surface split"),
            ("head_to_head", "Head-to-head history"),
            ("fatigue_match_length", "Fatigue / match length"),
        ),
    ),
    "mma": SportProfile(
        key="mma",
        label="UFC / MMA",
        leagues=("UFC", "MMA"),
        default_home_mean=0.55,
        default_away_mean=0.45,
        default_home_sd=0.2,
        default_away_sd=0.2,
        default_correlation=0.0,
        markets=("fight_winner", "method_of_victory", "round_betting", "total_rounds"),
        metrics=(
            ("striking_accuracy", "Striking accuracy"),
            ("striking_defense", "Striking defense"),
            ("takedown_defense", "Takedown defense %"),
            ("control_time", "Control time"),
            ("reach_height_differential", "Reach / height differential"),
            ("cardio_altitude_factor", "Cardio / altitude factor"),
            ("stance_matchup", "Stance matchup"),
        ),
    ),
}


def normalize_sport(sport: str | None) -> str:
    value = (sport or "basketball").strip().lower().replace(" ", "_")
    aliases = {
        "nba": "basketball",
        "ncaa_basketball": "basketball",
        "nfl": "football",
        "ncaa_football": "football",
        "mlb": "baseball",
        "nhl": "hockey",
        "epl": "soccer",
        "ucl": "soccer",
        "mls": "soccer",
        "ufc": "mma",
        "ufc_mma": "mma",
    }
    return aliases.get(value, value)


def get_sport_profile(sport: str | None) -> SportProfile:
    key = normalize_sport(sport)
    return SPORT_PROFILES.get(key, SPORT_PROFILES["basketball"])
