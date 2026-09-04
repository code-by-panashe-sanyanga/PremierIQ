# Static lat/lon for Premier League stadiums, keyed by football-data.org team id.
# football-data.org gives venue names but not coordinates, so we maintain this ourselves.
STADIUM_COORDS = {
    57: {"stadium": "Emirates Stadium", "city": "London", "lat": 51.5549, "lon": -0.1084},
    58: {"stadium": "Villa Park", "city": "Birmingham", "lat": 52.5090, "lon": -1.8848},
    61: {"stadium": "Stamford Bridge", "city": "London", "lat": 51.4817, "lon": -0.1910},
    62: {"stadium": "Hill Dickinson Stadium", "city": "Liverpool", "lat": 53.4250, "lon": -3.0024},
    63: {"stadium": "Craven Cottage", "city": "London", "lat": 51.4749, "lon": -0.2216},
    64: {"stadium": "Anfield", "city": "Liverpool", "lat": 53.4308, "lon": -2.9608},
    65: {"stadium": "Etihad Stadium", "city": "Manchester", "lat": 53.4831, "lon": -2.2004},
    66: {"stadium": "Old Trafford", "city": "Manchester", "lat": 53.4631, "lon": -2.2913},
    67: {"stadium": "St. James' Park", "city": "Newcastle", "lat": 54.9756, "lon": -1.6217},
    71: {"stadium": "Stadium of Light", "city": "Sunderland", "lat": 54.9143, "lon": -1.3883},
    73: {"stadium": "Tottenham Hotspur Stadium", "city": "London", "lat": 51.6043, "lon": -0.0664},
    76: {"stadium": "Molineux Stadium", "city": "Wolverhampton", "lat": 52.5903, "lon": -2.1304},
    322: {"stadium": "MKM Stadium", "city": "Hull", "lat": 53.7461, "lon": -0.3665},
    341: {"stadium": "Elland Road", "city": "Leeds", "lat": 53.7778, "lon": -1.5722},
    349: {"stadium": "Portman Road", "city": "Ipswich", "lat": 52.0555, "lon": 1.1450},
    351: {"stadium": "The City Ground", "city": "Nottingham", "lat": 52.9400, "lon": -1.1328},
    328: {"stadium": "Turf Moor", "city": "Burnley", "lat": 53.7890, "lon": -2.2302},
    338: {"stadium": "King Power Stadium", "city": "Leicester", "lat": 52.6204, "lon": -1.1422},
    340: {"stadium": "St Mary's Stadium", "city": "Southampton", "lat": 50.9058, "lon": -1.3911},
    345: {"stadium": "Bramall Lane", "city": "Sheffield", "lat": 53.3703, "lon": -1.4709},
    354: {"stadium": "Selhurst Park", "city": "London", "lat": 51.3983, "lon": -0.0856},
    397: {"stadium": "American Express Stadium", "city": "Brighton", "lat": 50.8617, "lon": -0.0837},
    402: {"stadium": "Gtech Community Stadium", "city": "London", "lat": 51.4907, "lon": -0.2886},
    563: {"stadium": "London Stadium", "city": "London", "lat": 51.5383, "lon": -0.0166},
    1044: {"stadium": "Vitality Stadium", "city": "Bournemouth", "lat": 50.7352, "lon": -1.8380},
    1076: {"stadium": "Coventry Building Society Arena", "city": "Coventry", "lat": 52.4483, "lon": -1.4952},
}

DEFAULT_STADIUM = {"stadium": "Unknown Stadium", "city": "Unknown", "lat": 51.5074, "lon": -0.1278}


def stadium_for(team_id: int) -> dict:
    return STADIUM_COORDS.get(team_id, DEFAULT_STADIUM)
