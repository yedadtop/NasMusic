package com.nasmusic.tv;

import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;

import androidx.annotation.NonNull;
import androidx.recyclerview.widget.GridLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import java.util.ArrayList;
import java.util.List;

/**
 * 歌手 / 专辑网格。封面尺寸按网格列宽自适应算出来，
 * 避免固定 dp 在不同列数下溢出被裁切。
 */
public class CardAdapter extends RecyclerView.Adapter<CardAdapter.VH> {

    public interface OnCardClick {
        void onCardClick(Collection item);
    }

    private final List<Collection> data = new ArrayList<>();
    private final OnCardClick listener;
    private final int fallbackSizeDp;

    public CardAdapter(int fallbackSizeDp, OnCardClick listener) {
        this.fallbackSizeDp = fallbackSizeDp;
        this.listener = listener;
        setHasStableIds(true);
    }

    public void submit(List<Collection> items) {
        data.clear();
        if (items != null) {
            data.addAll(items);
        }
        notifyDataSetChanged();
    }

    @Override
    public long getItemId(int position) {
        Collection c = data.get(position);
        return c.type * 100000L + c.id;
    }

    @Override
    public int getItemCount() {
        return data.size();
    }

    @NonNull
    @Override
    public VH onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View v = LayoutInflater.from(parent.getContext()).inflate(R.layout.item_card, parent, false);
        return new VH(v);
    }

    @Override
    public void onBindViewHolder(@NonNull VH h, int position) {
        Collection c = data.get(position);
        h.title.setText(c.name);
        h.subtitle.setText(c.subtitle);
        if (c.type == Collection.ARTIST) {
            // 圆形封面不能留方形占位底，否则四角会露出深色方块
            h.cover.setBackground(null);
        } else {
            h.cover.setBackground(h.itemView.getContext().getResources()
                    .getDrawable(R.drawable.bg_cover_placeholder,
                            h.itemView.getContext().getTheme()));
        }
        ImageLoader.load(h.cover, c.cover, c.type == Collection.ARTIST ? -1 : 12);
        h.resize(resolveCoverSize(h.itemView, fallbackSizeDp));
        h.itemView.setOnClickListener(v -> {
            if (listener != null) {
                listener.onCardClick(c);
            }
        });
    }

    /** 用当前网格列数算出封面边长，留出卡片内边距 */
    private static int resolveCoverSize(View item, int fallbackDp) {
        int density = Math.max(1, (int) item.getResources().getDisplayMetrics().density);
        ViewGroup parent = item.getParent() instanceof ViewGroup ? (ViewGroup) item.getParent() : null;
        if (parent instanceof RecyclerView) {
            RecyclerView rv = (RecyclerView) parent;
            RecyclerView.LayoutManager lm = rv.getLayoutManager();
            if (lm instanceof GridLayoutManager) {
                int span = Math.max(1, ((GridLayoutManager) lm).getSpanCount());
                int width = rv.getWidth() - rv.getPaddingLeft() - rv.getPaddingRight();
                if (width > 0) {
                    return Math.max(fallbackDp * density, width / span - 16 * density);
                }
            }
        }
        return fallbackDp * density;
    }

    static class VH extends RecyclerView.ViewHolder {
        final ImageView cover;
        final TextView title;
        final TextView subtitle;

        VH(@NonNull View v) {
            super(v);
            cover = v.findViewById(R.id.cover);
            title = v.findViewById(R.id.title);
            subtitle = v.findViewById(R.id.subtitle);
            v.setOnFocusChangeListener((view, has) -> {
                // 1.05 内的放大仍在网格留白里，选中框四边不会被裁
                view.animate()
                        .scaleX(has ? 1.05f : 1f)
                        .scaleY(has ? 1.05f : 1f)
                        .setDuration(160)
                        .start();
                view.setElevation(has ? dp(view, 16) : 0);
            });
        }

        void resize(int px) {
            LinearLayout.LayoutParams lp = (LinearLayout.LayoutParams) cover.getLayoutParams();
            if (lp.width != px || lp.height != px) {
                lp.width = px;
                lp.height = px;
                cover.setLayoutParams(lp);
            }
        }

        private static int dp(View v, int value) {
            return Math.round(value * v.getResources().getDisplayMetrics().density);
        }
    }
}
