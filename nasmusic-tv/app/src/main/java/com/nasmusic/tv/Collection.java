package com.nasmusic.tv;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.List;

/** 歌手 / 专辑。两者字段高度重合，用同一个类承载，靠 type 区分展示方式。 */
public class Collection {
    public static final int ARTIST = 0;
    public static final int ALBUM = 1;

    public int type;
    public int id;
    public String name = "";
    public String subtitle = "";
    public String cover = "";
    public int trackCount;
    public List<Track> tracks = new ArrayList<>();

    public static Collection artist(JSONObject o) {
        Collection c = new Collection();
        c.type = ARTIST;
        c.id = o.optInt("id");
        c.name = o.optString("name", "");
        c.cover = o.optString("cover", "");
        c.trackCount = o.optInt("track_count", 0);
        int albums = o.optInt("album_count", 0);
        c.subtitle = c.trackCount + " 首 · " + albums + " 张专辑";
        JSONArray arr = o.optJSONArray("tracks");
        if (arr != null) {
            c.tracks = Track.list(arr);
        }
        return c;
    }

    public static Collection album(JSONObject o) {
        Collection c = new Collection();
        c.type = ALBUM;
        c.id = o.optInt("id");
        c.name = o.optString("title", "");
        c.subtitle = o.optString("artist_name", "");
        c.cover = o.optString("cover", "");
        c.trackCount = o.optInt("track_count", 0);
        JSONArray arr = o.optJSONArray("tracks");
        if (arr != null) {
            c.tracks = Track.list(arr);
        }
        return c;
    }

    public static List<Collection> list(JSONArray arr, int type) {
        List<Collection> out = new ArrayList<>();
        if (arr == null) {
            return out;
        }
        for (int i = 0; i < arr.length(); i++) {
            JSONObject o = arr.optJSONObject(i);
            if (o == null) {
                continue;
            }
            out.add(type == ARTIST ? artist(o) : album(o));
        }
        return out;
    }
}
