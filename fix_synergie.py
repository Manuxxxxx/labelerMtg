import json

INPUT_FILE = "generated_synergies20250623203218.json"

# load file
with open(INPUT_FILE, "r") as file:
    data = json.load(file)


# Mapping function
def transform(cards):
    new_cards = []
    for card in cards:
        # Extract card names and synergy values
        new_card = {
            "card1": {"name": card["card1"]},
            "card2": {"name": card["card2"]},
        }
        if "synergy_predicted" in card:
            new_card["synergy_predicted"] = card["synergy_predicted"]
        if "synergy_manual" in card:
            new_card["synergy_manual"] = card["synergy_manual"]

        new_cards.append(new_card)
    return new_cards


# Output result
transformed = transform(data)
# Save the transformed data
with open(INPUT_FILE, "w") as file:
    json.dump(transformed, file, indent=4)
