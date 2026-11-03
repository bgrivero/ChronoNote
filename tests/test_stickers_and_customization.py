def test_stickers_presets_and_custom_upload(client):
    # 1. Fetch presets
    res = client.get("/api/stickers")
    assert res.status_code == 200
    stickers = res.json()
    assert len(stickers) >= 8
    names = [s["name"] for s in stickers]
    assert "Coffee Cup" in names
    assert "Gold Star" in names

    # 2. Upload custom sticker
    upload_res = client.post(
        "/api/stickers",
        json={
            "name": "Custom Heart Stamp",
            "category": "custom",
            "image_url": "data:image/svg+xml;utf8,<svg><text>❤️</text></svg>",
        },
    )
    assert upload_res.status_code == 201
    custom_stk = upload_res.json()
    assert custom_stk["name"] == "Custom Heart Stamp"
    assert custom_stk["category"] == "custom"

    # 3. Filter by category
    filter_res = client.get("/api/stickers?category=custom")
    assert filter_res.status_code == 200
    custom_list = filter_res.json()
    assert any(s["id"] == custom_stk["id"] for s in custom_list)

    # 4. Delete sticker
    del_res = client.delete(f"/api/stickers/{custom_stk['id']}")
    assert del_res.status_code == 200


def test_sticker_placements_on_calendar_and_notes(client):
    # 1. Place a sticker on calendar date 2026-11-15
    place_cal = client.post(
        "/api/stickers/placements",
        json={
            "sticker_name": "Gold Star",
            "image_url": "data:image/svg+xml;utf8,<svg><text>⭐</text></svg>",
            "target_type": "calendar_date",
            "target_key": "2026-11-15",
            "pos_x": 75,
            "pos_y": 20,
            "rotation_deg": 12,
            "scale": 110,
        },
    )
    assert place_cal.status_code == 201
    cal_placement = place_cal.json()
    assert cal_placement["target_type"] == "calendar_date"
    assert cal_placement["target_key"] == "2026-11-15"
    assert cal_placement["rotation_deg"] == 12

    # 2. Place a sticker on a note
    place_note = client.post(
        "/api/stickers/placements",
        json={
            "sticker_name": "Coffee Cup",
            "image_url": "data:image/svg+xml;utf8,<svg><text>☕</text></svg>",
            "target_type": "note",
            "target_key": "note-deep-work",
            "pos_x": 85,
            "pos_y": 10,
            "rotation_deg": -8,
            "scale": 90,
        },
    )
    assert place_note.status_code == 201
    note_placement = place_note.json()

    # 3. List placements by target_key
    list_res = client.get("/api/stickers/placements?target_type=calendar_date&target_key=2026-11-15")
    assert list_res.status_code == 200
    items = list_res.json()
    assert len(items) == 1
    assert items[0]["id"] == cal_placement["id"]

    # 4. Update placement position / rotation
    patch_res = client.patch(
        f"/api/stickers/placements/{cal_placement['id']}",
        json={"pos_x": 80, "rotation_deg": 20},
    )
    assert patch_res.status_code == 200
    updated = patch_res.json()
    assert updated["pos_x"] == 80
    assert updated["rotation_deg"] == 20

    # 5. Delete placements
    client.delete(f"/api/stickers/placements/{cal_placement['id']}")
    client.delete(f"/api/stickers/placements/{note_placement['id']}")
    assert len(client.get("/api/stickers/placements?target_key=2026-11-15").json()) == 0
