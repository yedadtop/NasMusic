package com.nasmusic.tv;

import android.content.res.ColorStateList;
import android.graphics.Color;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ImageView;
import android.widget.TextView;

import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;

import java.util.ArrayList;
import java.util.List;

/**
 * 歌曲列表。tvOS 风格：聚焦行整行变浅、文字转黑，
 * 配合轻抬升（scale + elevation）在 3 米外也能一眼看清焦点。
 */
public class TrackAdapter extends RecyclerView.Adapter<TrackAdapter.VH> {

    public interface OnTrackClick {
        void onTrackClick(List<Track> data, int position);
    }

    private final List<Track> data = new ArrayList<>();
    private final OnTrackClick listener;
    private int playingId = -1;

    public TrackAdapter(OnTrackClick listener) {
        this.listener = listener;
        setHasStableIds(true);
    }

    public void submit(List<Track> items) {
        data.clear();
        if (items != null) {
            data.addAll(items);
        }
        notifyDataSetChanged();
    }

    public List<Track> items() {
        return data;
    }

    public void setPlayingId(int id) {
        if (playingId == id) {
            return;
        }
        playingId = id;
        notifyDataSetChanged();
    }

    @Override
    public long getItemId(int position) {
        return data.get(position).id;
    }

    @Override
    public int getItemCount() {
        return data.size();
    }

    @NonNull
    @Override
    public VH onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View v = LayoutInflater.from(parent.getContext()).inflate(R.layout.item_track, parent, false);
        return new VH(v);
    }

    @Override
    public void onBindViewHolder(@NonNull VH h, int position) {
        Track t = data.get(position);
        h.title.setText(t.title);
        h.artist.setText(t.subtitle());
        h.duration.setText(t.durationText());
        h.format.setText(t.format == null ? "" : t.format.toUpperCase());
        h.format.setVisibility(t.format == null || t.format.isEmpty() ? View.GONE : View.VISIBLE);
        h.playing.setVisibility(t.id == playingId ? View.VISIBLE : View.INVISIBLE);
        ImageLoader.load(h.cover, t.cover, 8);
        h.style(h.itemView.hasFocus());
        h.itemView.setOnClickListener(v -> {
            if (listener != null) {
                listener.onTrackClick(data, h.getBindingAdapterPosition());
            }
        });
    }

    static class VH extends RecyclerView.ViewHolder {
        final ImageView cover;
        final TextView title;
        final TextView artist;
        final TextView duration;
        final TextView format;
        final View playing;

        VH(@NonNull View v) {
            super(v);
            cover = v.findViewById(R.id.cover);
            title = v.findViewById(R.id.title);
            artist = v.findViewById(R.id.artist);
            duration = v.findViewById(R.id.duration);
            format = v.findViewById(R.id.format);
            playing = v.findViewById(R.id.playing_bar);

            v.setOnFocusChangeListener((view, has) -> {
                // 行本身已是整行白色，不再做缩放：放大后会超出列表边界，左右圆角被裁掉
                view.setElevation(has ? dp(view, 8) : 0);
                style(has);
            });
        }

        void style(boolean light) {
            title.setTextColor(light ? Color.BLACK : 0xFFFFFFFF);
            artist.setTextColor(light ? 0xFF6E6E73 : 0xFFA1A1A6);
            duration.setTextColor(light ? 0xFF6E6E73 : 0xFFA1A1A6);
            format.setTextColor(light ? 0xFF6E6E73 : 0xFF6E6E73);
            if (format.getBackground() != null) {
                format.setBackgroundTintList(ColorStateList.valueOf(light ? 0x12000000 : 0x1AFFFFFF));
            }
        }

        private static int dp(View v, int value) {
            return Math.round(value * v.getResources().getDisplayMetrics().density);
        }
    }
}
