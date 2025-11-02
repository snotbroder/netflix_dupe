// Select all cards
const cards = document.querySelectorAll('.card-container');

cards.forEach(card => {
  card.addEventListener('mouseover', () => {
    // Remove .card-active from all cards
    cards.forEach(c => c.classList.remove('card-active'));

    // Add .card-active to the hovered card
    card.classList.add('card-active');
    console.log("added class")
});

card.addEventListener('mouseout', () => {
    // Optional: remove the class when mouse leaves
    card.classList.remove('card-active');
    console.log("removed class")
  });
});