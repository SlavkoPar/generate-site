// Always offered in the "Load a previous request" dropdown, after the user's own history.
// The second one is a refinement: run it after the first so Claude adds the cart to that site.
export const DEFAULT_PROMPTS = [
  `Generate Site with
- Header
- NavBar (left side)
- Footer

In NavBar create groups:
Fruit
- Apple
- Pear
- Banana
Vegetables
- Carrots
- Onions
- Garlic
- Cabbage
- Potatoes
For each item create icon (not for Groups) and create linked page with icon and some characteristics, including dummy price.
Enable Expand/Collapse of the groups.`,
  'Add shopping cart to the site.',
]
