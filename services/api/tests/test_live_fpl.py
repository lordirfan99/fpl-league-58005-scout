from app import live_fpl


def test_league_standings_fetches_every_official_page_and_deduplicates(monkeypatch) -> None:
    pages = {
        1: {"standings": {"has_next": True, "results": [{"entry": 1}, {"entry": 2}]}},
        2: {"standings": {"has_next": True, "results": [{"entry": 2}, {"entry": 3}]}},
        3: {"standings": {"has_next": False, "results": [{"entry": 4}]}},
    }

    def fake_get(path: str, ttl: int = 30) -> dict:
        assert ttl == 60
        page = int(path.split("page_standings=")[1].split("&", 1)[0])
        return pages[page]

    monkeypatch.setattr(live_fpl, "_get", fake_get)
    result = live_fpl.league_standings(58005)

    assert result["count"] == 4
    assert result["pages_fetched"] == 3
    assert [row["entry"] for row in result["managers"]] == [1, 2, 3, 4]
