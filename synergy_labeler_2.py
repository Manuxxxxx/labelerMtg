import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk, ImageDraw
import json
import os
import requests
from io import BytesIO
import tkinter.font as tkFont

# === CONFIG ===
BULK_FILE = "cards_with_tags_20250622170831_withuri.json"
SYNERGY_FILE = "generated_synergies20250623203218.json"
SYNERGY_FILE_TMP = "synergies_tmp.json"
IMAGE_CACHE_DIR = "image-dataset/"

UI_SCALE = 1.0
IMAGE_SCALE = 2
FONT_SIZE = 10


def s(value):
    return int(value * UI_SCALE)


def sf(size_tuple):
    family = size_tuple[0]
    try:
        return tuple([family] + [int(size_tuple[1] * UI_SCALE)] + list(size_tuple[2:]))
    except:
        return ("Arial", int(size_tuple[1] * UI_SCALE))


def load_json(file):
    with open(file, "r", encoding="utf-8") as f:
        content = f.read().strip()
        if not content:
            return []
        return json.loads(content)


def save_json(data, file):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_or_download_image(card):
    os.makedirs(IMAGE_CACHE_DIR, exist_ok=True)
    name = card["name"].replace("/", "_").replace(" ", "_")
    image_path = os.path.join(IMAGE_CACHE_DIR, f"{name}.png")

    if os.path.exists(image_path):
        img = Image.open(image_path)
    else:
        url = card.get("image_uris", {}).get("png")
        if not url:
            # Load a placeholder image (gray with "No image")
            img = Image.new("RGB", (300, 420), color="gray")
            draw = ImageDraw.Draw(img)
            draw.text((10, 190), "No Image", fill="black")
            img.save(image_path)
        else:
            response = requests.get(url)
            img = Image.open(BytesIO(response.content))
            img.save(image_path)
    return img


def resize_image(img, height=400):
    height = int(height * IMAGE_SCALE)
    w, h = img.size
    new_w = int((height / h) * w)
    return img.resize((new_w, height), Image.LANCZOS)


class SynergyApp:
    def __init__(self, root):
        self.merge_synergies_files()
        self.root = root
        self.root.title("MTG Synergy Labeler")
        self.root.configure(bg="#f0f0f0")

        self.cards = load_json(BULK_FILE)
        self.card_lookup = {card["name"]: card for card in self.cards}

        self.synergy_entries = load_json(SYNERGY_FILE)
        self.synergies_without_manual = [
            entry
            for entry in self.synergy_entries
            if entry.get("synergy_manual") is None
        ]
        self.synergies_labeled_this_session = []

        self.already_labeled_number = len(self.synergy_entries) - len(
            self.synergies_without_manual
        )

        # Now we include all synergy entries to navigate all pairs
        self.current_ptr = 0  # pointer into synergy_entries list

        self.setup_ui()
        self.display_current_pair()

    def merge_synergies_files(self):
        """
        Merges the synergies.json file with the synergies_tmp.json file.
        This is useful for saving progress without losing existing entries.
        """
        if not os.path.exists(SYNERGY_FILE_TMP):
            print("No TMP FILE")
            return
        synergies_tmp = load_json(SYNERGY_FILE_TMP)
        synergies = load_json(SYNERGY_FILE)

        # Merge synergies, avoiding duplicates
        existing_synergies = {
            f"{entry['card1']}_{entry['card2']}": entry for entry in synergies
        }
        for entry in synergies_tmp:
            key = f"{entry['card1']}_{entry['card2']}"
            if key in existing_synergies:
                existing_synergies[key]["synergy_manual"] = entry["synergy_manual"]
        merged_synergies = list(existing_synergies.values())
        save_json(merged_synergies, SYNERGY_FILE)

        open(SYNERGY_FILE_TMP, "w").close()

    def get_current_entry(self):
        entry = self.synergies_without_manual[self.current_ptr]
        card1 = self.card_lookup.get(entry["card1"]["name"])
        card2 = self.card_lookup.get(entry["card2"]["name"])
        entry
        return card1, card2, entry

    def synergy_color(self, manual):
        """
        Return a color hex string for a synergy value between -1 and 1:
        -1 = red (#ff0000)
        0 = gray (#888888)
        1 = green (#00ff00)
        Works smoothly for intermediate values like -0.5 and 0.5.
        """
        if manual is None:
            return "#000000"  # default color when no manual synergy

        val = max(min(manual, 1), -1)  # Clamp to [-1,1]

        if val == 0:
            return "#888888"  # gray for zero

        if val > 0:
            # Gradient from gray to green
            r = int(136 * (1 - val))  # from 136 to 0
            g = int(136 + (255 - 136) * val)  # from 136 to 255
            b = int(136 * (1 - val))  # from 136 to 0
        else:
            # Gradient from gray to red
            r = int(136 + (255 - 136) * (-val))  # from 136 to 255
            g = int(136 * (1 + val))  # from 136 to 0
            b = int(136 * (1 + val))  # from 136 to 0

        return f"#{r:02x}{g:02x}{b:02x}"

    def display_current_pair(self):
        try:
            card1, card2, entry = self.get_current_entry()
        except IndexError:
            self.status_label.config(text="No synergy entries to display.")
            return

        if not card1 or not card2:
            self.status_label.config(text="One or both cards not found.")
            return

        for i, card in enumerate([card1, card2]):
            img = load_or_download_image(card)
            if img:
                img = resize_image(img)
                tk_img = ImageTk.PhotoImage(img)
                self.image_labels[i].configure(image=tk_img)
                self.image_labels[i].image = tk_img

            text = f"Name: {card['name']}\nType: {card['type_line']}\nText: {card.get('oracle_text', '')}"
            if "power" in card:
                text += f"\nP/T: {card['power']} / {card['toughness']}"
            self.text_boxes[i].config(state="normal")
            self.text_boxes[i].delete("1.0", tk.END)
            self.text_boxes[i].insert(tk.END, text)
            self.text_boxes[i].config(state="disabled")
            self.text_vars[i].set(card["name"])

        pred = entry.get("synergy_predicted", "N/A")
        manual = entry.get("synergy_manual", None)
        synergy_edhrec = entry.get("synergy_edhrec", None)

        manual_str = manual

        self.info_label.config(text=f"Predicted synergy: {pred:.2f} / ")
        self.manual_label.config(text=f"Manual synergy: {manual_str}")

        self.manual_label.config(fg=self.synergy_color(manual))

        if manual is None:
            # No synergy labeled yet: enable all buttons
            for button_dict in self.buttons.values():
                button_dict["button"].config(state="normal")
        else:
            # Disable the button with the current manual value,
            # enable all others
            for button_dict in self.buttons.values():
                if button_dict["value"] == manual:
                    button_dict["button"].config(state="disabled")
                else:
                    button_dict["button"].config(state="normal")

        # Back button enable only if not at first entry
        self.back_btn.config(state="normal" if self.current_ptr > 0 else "disabled")
        # Next button enable only if not at last entry
        self.next_btn.config(
            state=(
                "normal"
                if self.current_ptr < len(self.synergies_without_manual) - 1
                else "disabled"
            )
        )

        self.number_entry_label.config(
            text=f"Entry {self.current_ptr + 1} / {len(self.synergies_without_manual)}"
        )

        self.labeled_number_label.config(
            text=f"Labeled pairs: {self.already_labeled_number} / {len(self.synergy_entries)}"
        )

    def label_synergy(self, value):

        if (
            self.synergies_without_manual[self.current_ptr].get("synergy_manual", None)
            is None
        ):
            self.synergies_without_manual[self.current_ptr]["synergy_manual"] = value
            self.already_labeled_number += 1
            self.synergies_labeled_this_session.append(
                self.synergies_without_manual[self.current_ptr]
            )
        else:
            self.synergies_without_manual[self.current_ptr]["synergy_manual"] = value
            for i in range(len(self.synergies_labeled_this_session)):
                synergy_i = self.synergies_labeled_this_session[i]
                if (
                    synergy_i["card1"]["name"]
                    == self.synergies_without_manual[self.current_ptr]["card1"]["name"]
                    and synergy_i["card2"]["name"]
                    == self.synergies_without_manual[self.current_ptr]["card2"]["name"]
                ):
                    self.synergies_labeled_this_session[i] = (
                        self.synergies_without_manual[self.current_ptr]
                    )

        save_json(self.synergies_labeled_this_session, SYNERGY_FILE_TMP)
        self.display_current_pair()  # refresh UI buttons etc.

    def jump_to_synergy(self):
        val = self.jump_var.get()
        try:
            n = int(val)
            if 1 <= n <= len(self.synergies_without_manual):
                self.current_ptr = n - 1
                self.display_current_pair()
            else:
                self.status_label.config(
                    text=f"Enter a number between 1 and {len(self.synergies_without_manual)}"
                )
        except ValueError:
            self.status_label.config(text="Please enter a valid integer")

    def go_next(self):
        if self.current_ptr < len(self.synergies_without_manual) - 1:
            self.current_ptr += 1
            self.display_current_pair()

    def go_back(self):
        if self.current_ptr > 0:
            self.current_ptr -= 1
            self.display_current_pair()

    def setup_ui(self):
        self.card_frames = []
        self.image_labels = []
        self.text_boxes = []
        self.search_boxes = []
        self.text_vars = []

        top_frame = tk.Frame(self.root, bg="#f0f0f0")
        top_frame.pack(fill="both", expand=True)

        for side in [0, 1]:
            frame = tk.Frame(top_frame, bg="#f0f0f0")
            frame.pack(side="left", fill="both", expand=True, padx=s(10), pady=s(10))

            img_label = tk.Label(frame, bg="#f0f0f0")
            img_label.pack()

            text = tk.Text(
                frame,
                height=s(10),
                width=s(60),
                wrap="word",
                font=sf(("Arial", FONT_SIZE)),
                state="disabled",
            )
            text.pack()

            var = tk.StringVar()
            search = ttk.Combobox(
                frame,
                textvariable=var,
                font=sf(("Arial", FONT_SIZE)),
            )
            search.pack(pady=s(5), fill="x")
            search.bind("<KeyRelease>", lambda e, s=side: self.update_suggestions(e, s))
            search.bind(
                "<<ComboboxSelected>>", lambda e, s=side: self.replace_card(e, s)
            )

            self.card_frames.append(frame)
            self.image_labels.append(img_label)
            self.text_boxes.append(text)
            self.search_boxes.append(search)
            self.text_vars.append(var)

        self.info_label = tk.Label(
            self.root,
            text="",
            fg="blue",
            font=sf(("Arial", FONT_SIZE)),
            bg="#f0f0f0",
        )
        self.info_label.pack(pady=s(5))

        self.manual_label = tk.Label(
            self.root,
            text="",
            fg="blue",
            font=sf(("Arial", FONT_SIZE, "bold")),
            bg="#f0f0f0",
        )
        self.manual_label.pack(pady=s(5))

        button_frame = tk.Frame(self.root, bg="#f0f0f0")
        button_frame.pack(pady=s(10))

        self.back_btn = tk.Button(
            button_frame,
            text="Back",
            command=self.go_back,
            width=s(30),
            height=s(2),
            font=sf(("Arial", FONT_SIZE)),
        )
        self.back_btn.pack(side="left", padx=s(5))

        self.buttons = {
            "synergy": {"value": 1.0},
            "half-synergy": {"value": 0.5},
            "no": {"value": 0.0},
            "half negative": {"value": -0.5},
            "negative": {"value": -1},
        }

        for label, val_dict in self.buttons.items():
            val = val_dict["value"]
            btn = tk.Button(
                button_frame,
                text=label.upper(),
                command=lambda v=val: self.label_synergy(v),
                width=s(20),
                height=s(2),
                font=sf(("Arial", FONT_SIZE)),
                bg=self.synergy_color(val),
            )
            btn.pack(side="left", padx=s(5))
            val_dict["button"] = btn

        self.next_btn = tk.Button(
            button_frame,
            text="Next",
            command=self.go_next,
            width=s(30),
            height=s(2),
            font=sf(("Arial", FONT_SIZE)),
        )
        self.next_btn.pack(side="left", padx=s(5))

        # Add this inside setup_ui(), after creating back_btn and next_btn buttons

        jump_frame = tk.Frame(button_frame, bg="#f0f0f0")
        jump_frame.pack(side="left", padx=s(5))

        self.jump_var = tk.StringVar()
        jump_entry = tk.Entry(
            jump_frame,
            textvariable=self.jump_var,
            width=5,
            font=sf(("Noto Sans Inscriptional Pahlavi", FONT_SIZE)),
        )
        jump_entry.pack(side="left")

        jump_btn = tk.Button(
            jump_frame,
            text="Go",
            command=self.jump_to_synergy,
            font=sf(("Noto Sans Inscriptional Pahlavi", FONT_SIZE)),
        )
        jump_btn.pack(side="left", padx=(5, 0))

        self.status_label = tk.Label(
            self.root,
            text="",
            font=sf(("Arial", FONT_SIZE + 2, "bold")),
            fg="black",
            bg="#f0f0f0",
        )
        self.status_label.pack(pady=s(5))

        self.number_entry_label = tk.Label(
            self.root,
            text="None",
            font=sf(("Arial", FONT_SIZE)),
            fg="black",
            bg="#f0f0f0",
        )
        self.number_entry_label.pack(pady=s(5))

        self.labeled_number_label = tk.Label(
            self.root,
            text="",
            font=sf(("Arial", FONT_SIZE)),
            fg="black",
            bg="#f0f0f0",
        )
        self.labeled_number_label.pack(pady=s(5))

    def update_suggestions(self, event, index):
        typed = self.text_vars[index].get().lower()
        suggestions = [c["name"] for c in self.cards if typed in c["name"].lower()][:10]
        self.search_boxes[index]["values"] = suggestions

    def replace_card(self, event, index):
        name = self.text_vars[index].get()
        match = self.card_lookup.get(name)
        if match:
            entry = self.synergies_without_manual[self.current_index]
            if index == 0:
                entry["card1"]["name"] = name
            else:
                entry["card2"]["name"] = name
            self.display_current_pair()


if __name__ == "__main__":
    root = tk.Tk()
    app = SynergyApp(root)
    root.mainloop()
