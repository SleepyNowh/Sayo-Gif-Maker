# well here ya go enjoy the tool

# DEPENDENCIES - paste this into ur console to install
# pip3 install pillow imageio "imageio[pyav]" imageio-ffmpeg

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import math
from PIL import Image, ImageTk, ImageSequence
import imageio.v3 as iio

TARGET_W = 160
TARGET_H = 80
MAX_FRAMES = 6969
MAX_BYTES = 200_000  # this is for the max kbs it allows please modify if im wrong


def load_frames_from_gif(path: str) -> tuple[list[Image.Image], float]:
    img = Image.open(path)
    frames = []
    durations = []
    for frame in ImageSequence.Iterator(img):
        frames.append(frame.convert("RGBA"))
        durations.append(frame.info.get("duration", 100))
    fps = 1000 / (sum(durations) / len(durations)) if durations else 10
    return frames, fps


def load_frames_from_mp4(path: str, start_s: float, end_s: float) -> tuple[list[Image.Image], float]:
    reader = iio.imiter(path, plugin="pyav")
    meta = iio.immeta(path, plugin="pyav")
    fps = meta.get("fps", 24)

    frames = []
    frame_idx = 0
    for raw in reader:
        t = frame_idx / fps
        if t < start_s:
            frame_idx += 1
            continue
        if t > end_s:
            break
        frames.append(Image.fromarray(raw).convert("RGBA"))
        frame_idx += 1

    return frames, fps


def sample_frames(frames: list, n: int) -> list:
    if len(frames) <= n:
        return frames
    indices = [round(i * (len(frames) - 1) / (n - 1)) for i in range(n)]
    return [frames[i] for i in indices]


def resize_and_crop(frame: Image.Image, w: int, h: int) -> Image.Image:
    src_w, src_h = frame.size
    scale = max(w / src_w, h / src_h)
    new_w, new_h = math.ceil(src_w * scale), math.ceil(src_h * scale)
    frame = frame.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - w) // 2
    top = (new_h - h) // 2
    return frame.crop((left, top, left + w, top + h))


def frames_to_gif(frames: list[Image.Image], out_path: str, fps: float):
    delay_ms = max(10, int(1000 / fps))
    palette_frames = [f.convert("RGB").quantize(colors=256) for f in frames]
    palette_frames[0].save(
        out_path,
        save_all=True,
        append_images=palette_frames[1:],
        loop=0,
        duration=delay_ms,
        optimize=True,
    )


class O3CGifMaker(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sayo Device GIF Maker")
        self.resizable(False, False)
        self.configure(bg="#1e1e2e")

        self._input_path = tk.StringVar()
        self._start_s = tk.DoubleVar(value=0.0)
        self._end_s = tk.DoubleVar(value=5.0)
        self._frames_var = tk.IntVar(value=8)
        self._fps_var = tk.DoubleVar(value=8.0)
        self._duration_s = 0.0
        self._is_video = False
        self._preview_frames: list[Image.Image] = []
        self._preview_job = None

        self._build_ui()

    def _build_ui(self):
        PAD = 12
        BG = "#1e1e2e"
        FG = "#cdd6f4"
        ACCENT = "#89b4fa"
        CARD = "#313244"
        ENTRY_BG = "#45475a"

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TLabel", background=BG, foreground=FG, font=("Segoe UI", 10))
        style.configure("Title.TLabel", background=BG, foreground=ACCENT, font=("Segoe UI", 13, "bold"))
        style.configure("Card.TFrame", background=CARD, relief="flat")
        style.configure("TScale", background=BG, troughcolor=ENTRY_BG, sliderthickness=16)
        style.configure("TButton", background=ACCENT, foreground="#1e1e2e", font=("Segoe UI", 10, "bold"), padding=6)
        style.map("TButton", background=[("active", "#74c7ec")])
        style.configure("TSpinbox", fieldbackground=ENTRY_BG, foreground=FG, background=BG, arrowcolor=ACCENT)
        style.configure("TEntry", fieldbackground=ENTRY_BG, foreground=FG)
        style.configure("TProgressbar", troughcolor=ENTRY_BG, background=ACCENT)

        ttk.Label(self, text="Sayo Device GIF Maker", style="Title.TLabel").pack(pady=(PAD, 2))
        ttk.Label(self, text="Output: 160×80 px · <200 KB recommended", foreground="#a6adc8", background=BG).pack()

        fc = ttk.Frame(self, style="Card.TFrame", padding=PAD)
        fc.pack(fill="x", padx=PAD, pady=(PAD, 4))

        ttk.Label(fc, text="Input File (.mp4 or .gif)", background=CARD, foreground=ACCENT).grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Entry(fc, textvariable=self._input_path, width=40, style="TEntry").grid(row=1, column=0, columnspan=2, sticky="ew", pady=4)
        ttk.Button(fc, text="Browse…", command=self._browse).grid(row=1, column=2, padx=(6, 0))

        self._trim_frame = ttk.Frame(self, style="Card.TFrame", padding=PAD)
        self._trim_frame.pack(fill="x", padx=PAD, pady=4)

        ttk.Label(self._trim_frame, text="✂  Trim  (MP4 only)", background=CARD, foreground=ACCENT).grid(row=0, column=0, columnspan=4, sticky="w")

        ttk.Label(self._trim_frame, text="Start (s):", background=CARD).grid(row=1, column=0, sticky="w", pady=4)
        self._start_label = ttk.Label(self._trim_frame, text="0.0 s", background=CARD, foreground=ACCENT, width=7)
        self._start_label.grid(row=1, column=1, sticky="w")
        self._start_slider = ttk.Scale(self._trim_frame, from_=0, to=60, variable=self._start_s,
                                       orient="horizontal", length=260, command=self._on_start_slide)
        self._start_slider.grid(row=1, column=2, columnspan=2, padx=(6, 0))

        ttk.Label(self._trim_frame, text="End (s):", background=CARD).grid(row=2, column=0, sticky="w", pady=4)
        self._end_label = ttk.Label(self._trim_frame, text="5.0 s", background=CARD, foreground=ACCENT, width=7)
        self._end_label.grid(row=2, column=1, sticky="w")
        self._end_slider = ttk.Scale(self._trim_frame, from_=0, to=60, variable=self._end_s,
                                     orient="horizontal", length=260, command=self._on_end_slide)
        self._end_slider.grid(row=2, column=2, columnspan=2, padx=(6, 0))

        self._trim_info = ttk.Label(self._trim_frame, text="Load an MP4 to trim", background=CARD, foreground="#6c7086")
        self._trim_info.grid(row=3, column=0, columnspan=4, sticky="w")

        sc = ttk.Frame(self, style="Card.TFrame", padding=PAD)
        sc.pack(fill="x", padx=PAD, pady=4)

        ttk.Label(sc, text="Output Settings", background=CARD, foreground=ACCENT).grid(row=0, column=0, columnspan=4, sticky="w")

        ttk.Label(sc, text="Frames:", background=CARD).grid(row=1, column=0, sticky="w", pady=6)
        tk.Spinbox(sc, from_=1, to=MAX_FRAMES, textvariable=self._frames_var, width=5,
                   bg="#45475a", fg=FG, buttonbackground=CARD, relief="flat",
                   font=("Segoe UI", 10), command=self._schedule_preview).grid(row=1, column=1, padx=8)

        ttk.Label(sc, text="Playback FPS:", background=CARD).grid(row=1, column=2, sticky="w")
        tk.Spinbox(sc, from_=1, to=30, textvariable=self._fps_var, width=5, increment=1,
                   bg="#45475a", fg=FG, buttonbackground=CARD, relief="flat",
                   font=("Segoe UI", 10), command=self._schedule_preview).grid(row=1, column=3, padx=8)

        pc = ttk.Frame(self, style="Card.TFrame", padding=PAD)
        pc.pack(fill="x", padx=PAD, pady=4)

        ttk.Label(pc, text="👁  Preview  (160×80)", background=CARD, foreground=ACCENT).pack(anchor="w")
        self._preview_canvas = tk.Canvas(pc, width=TARGET_W, height=TARGET_H,
                                         bg="#11111b", highlightthickness=1, highlightbackground="#45475a")
        self._preview_canvas.pack(pady=(6, 0))
        self._preview_img_ref = None
        self._anim_frames: list[ImageTk.PhotoImage] = []
        self._anim_idx = 0

        self._size_label = ttk.Label(pc, text="Estimated output size —", background=CARD, foreground="#a6adc8")
        self._size_label.pack(anchor="w", pady=(4, 0))

        bc = ttk.Frame(self, style="Card.TFrame", padding=PAD)
        bc.pack(fill="x", padx=PAD, pady=(4, PAD))

        self._progress = ttk.Progressbar(bc, mode="indeterminate", length=340)
        self._progress.pack(fill="x", pady=(0, 8))

        self._status = ttk.Label(bc, text="Ready", background=CARD, foreground="#a6adc8")
        self._status.pack(anchor="w")

        ttk.Button(bc, text="Convert & Save GIF", command=self._convert).pack(pady=(8, 0), fill="x")

    def _browse(self):
        path = filedialog.askopenfilename(
            title="Select MP4 or GIF",
            filetypes=[("Video/GIF", "*.mp4 *.gif"), ("All files", "*.*")]
        )
        if not path:
            return
        self._input_path.set(path)
        self._is_video = path.lower().endswith(".mp4")
        self._load_source(path)

    def _load_source(self, path: str):
        self._status.config(text="Loading source…")
        self.update_idletasks()
        try:
            if self._is_video:
                meta = iio.immeta(path, plugin="pyav")
                dur = meta.get("duration", 10.0)
                fps = meta.get("fps", 24.0)
                self._duration_s = dur
                self._start_slider.config(to=dur)
                self._end_slider.config(to=dur)
                self._start_s.set(0.0)
                self._end_s.set(min(dur, 10.0))
                self._start_label.config(text=f"0.0 s")
                self._end_label.config(text=f"{min(dur, 10.0):.1f} s")
                self._trim_info.config(text=f"Duration: {dur:.1f} s  |  Source FPS: {fps:.1f}")
                self._status.config(text=f"MP4 loaded {dur:.1f}s @ {fps:.1f} fps")
            else:
                img = Image.open(path)
                n = getattr(img, 'n_frames', 1)
                dur_ms = img.info.get("duration", 100) * n
                self._trim_info.config(text="GIF loaded — trim not available")
                self._status.config(text=f"GIF loaded {n} frames.")
        except Exception as e:
            messagebox.showerror("Load Error", str(e))
            return
        self._schedule_preview()

    def _on_start_slide(self, val):
        v = float(val)
        if v >= self._end_s.get():
            self._start_s.set(self._end_s.get() - 0.1)
        self._start_label.config(text=f"{self._start_s.get():.1f} s")
        self._schedule_preview()

    def _on_end_slide(self, val):
        v = float(val)
        if v <= self._start_s.get():
            self._end_s.set(self._start_s.get() + 0.1)
        self._end_label.config(text=f"{self._end_s.get():.1f} s")
        self._schedule_preview()

    def _schedule_preview(self, *_):
        if self._preview_job:
            self.after_cancel(self._preview_job)
        self._preview_job = self.after(400, self._build_preview)

    def _build_preview(self):
        path = self._input_path.get()
        if not path or not os.path.exists(path):
            return
        n = max(1, self._frames_var.get())
        try:
            if self._is_video:
                raw, fps = load_frames_from_mp4(path, self._start_s.get(), self._end_s.get())
            else:
                raw, fps = load_frames_from_gif(path)
            sampled = sample_frames(raw, n)
            resized = [resize_and_crop(f, TARGET_W, TARGET_H) for f in sampled]
            self._preview_frames_pil = resized
            est = self._estimate_size(resized, self._fps_var.get())
            color = "#a6e3a1" if est < MAX_BYTES else "#f38ba8"
            self._size_label.config(text=f"Estimated output size: ~{est // 1024} KB  {'✓ OK' if est < MAX_BYTES else '⚠ May exceed 200 KB!'}", foreground=color)
            self._anim_frames = [ImageTk.PhotoImage(f.convert("RGB")) for f in resized]
            self._anim_idx = 0
            self._animate_preview()
        except Exception as e:
            self._status.config(text=f"Preview error: {e}")

    def _estimate_size(self, frames: list[Image.Image], fps: float) -> int:
        import io
        buf = io.BytesIO()
        delay_ms = max(10, int(1000 / max(fps, 1)))
        pf = [f.convert("RGB").quantize(colors=256) for f in frames]
        pf[0].save(buf, format="GIF", save_all=True, append_images=pf[1:], loop=0,
                   duration=delay_ms, optimize=True)
        return buf.tell()

    def _animate_preview(self):
        if not self._anim_frames:
            return
        img = self._anim_frames[self._anim_idx % len(self._anim_frames)]
        self._preview_canvas.delete("all")
        self._preview_canvas.create_image(0, 0, anchor="nw", image=img)
        self._preview_img_ref = img
        self._anim_idx += 1
        delay = max(50, int(1000 / max(self._fps_var.get(), 1)))
        self.after(delay, self._animate_preview)

    def _convert(self):
        path = self._input_path.get()
        if not path or not os.path.exists(path):
            messagebox.showwarning("No file", "Please select an input file first")
            return
        out = filedialog.asksaveasfilename(
            title="Save GIF As",
            defaultextension=".gif",
            filetypes=[("GIF", "*.gif")]
        )
        if not out:
            return
        self._progress.start(10)
        self._status.config(text="Converting…")
        threading.Thread(target=self._do_convert, args=(path, out), daemon=True).start()

    def _do_convert(self, path: str, out: str):
        try:
            n = max(1, self._frames_var.get())
            fps = max(1.0, self._fps_var.get())
            if self._is_video:
                raw, src_fps = load_frames_from_mp4(path, self._start_s.get(), self._end_s.get())
            else:
                raw, src_fps = load_frames_from_gif(path)
            sampled = sample_frames(raw, n)
            resized = [resize_and_crop(f, TARGET_W, TARGET_H) for f in sampled]
            frames_to_gif(resized, out, fps)
            size = os.path.getsize(out)
            msg = f"Saved! {len(resized)} frames · {size // 1024} KB"
            if size > MAX_BYTES:
                msg += "\n⚠ File exceeds 200 KB"
            self.after(0, lambda: self._done(msg, size > MAX_BYTES))
        except Exception as e:
            self.after(0, lambda: self._done(f"Error: {e}", True))

    def _done(self, msg: str, warn: bool):
        self._progress.stop()
        self._status.config(text=msg)
        if warn:
            messagebox.showwarning("Warning", msg)
        else:
            messagebox.showinfo("Done", msg)


if __name__ == "__main__":
    app = O3CGifMaker()
    app.mainloop()