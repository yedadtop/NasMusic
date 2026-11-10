package com.nasmusic.tv;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.List;

/** 一首歌。字段对应后端 /api/tracks/ 的返回。 */
public class Track {
    public int id;
    public String title = "";
    public String artistName = "";
    public String albumTitle = "";
    public String cover = "";
    public String format = "";
    public double duration;
    public String addedAt = "";
    /** LRC 文本。列表接口不返回，只有 /api/tracks/{id}/ 详情里带 */
    public String lyrics = "";

    public static Track from(JSONObject o) {
        Track t = new Track();
        t.id = o.optInt("id");
        t.title = o.optString("title", "");
        t.artistName = o.optString("artist_name", "");
        t.albumTitle = o.optString("album_title", "");
        t.cover = o.optString("track_cover", "");
        t.format = o.optString("format", "");
        t.duration = o.optDouble("duration", 0);
        t.addedAt = o.optString("added_at", "");
        t.lyrics = o.optString("lyrics", "");
        return t;
    }

    public static List<Track> list(JSONArray arr) {
        List<Track> out = new ArrayList<>();
        if (arr == null) {
            return out;
        }
        for (int i = 0; i < arr.length(); i++) {
            JSONObject o = arr.optJSONObject(i);
            if (o != null) {
                out.add(from(o));
            }
        }
        return out;
    }

    public String durationText() {
        int total = (int) Math.round(duration);
        return total / 60 + ":" + String.format("%02d", total % 60);
    }

    public String streamUrl() {
        return Api.base() + "/stream/" + id + "/";
    }

    public String subtitle() {
        if (artistName.isEmpty() && albumTitle.isEmpty()) {
            return "";
        }
        if (albumTitle.isEmpty()) {
            return artistName;
        }
        if (artistName.isEmpty()) {
            return albumTitle;
        }
        return artistName + " · " + albumTitle;
    }
}
