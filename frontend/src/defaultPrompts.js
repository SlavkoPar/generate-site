// The starting list of the "Load a previous request" dropdown, until the user sends their own.
// They build on each other: run them in order, so each one refines the site made by the first.
export const DEFAULT_PROMPTS = [
  `Generate Site with
- Header
- NavBar (left side)
- Footer`,
  `In NavBar create groups:
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
