// All open buttons
const showButtons = document.querySelectorAll(".openDialogBtn");

showButtons.forEach(button => {
  button.addEventListener("click", () => {
    const userPk = button.dataset.user; // get the user PK
    const dialog = document.getElementById(`dialog-${userPk}`);
    if (dialog) dialog.showModal();
  });
});

// Close buttons
const closeButtons = document.querySelectorAll(".closeDialogBtn");

closeButtons.forEach(button => {
  button.addEventListener("click", () => {
    const dialog = button.closest("dialog");
    if (dialog) dialog.close();
  });
});
