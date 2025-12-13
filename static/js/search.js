async function server(url, method, data_source_selector, function_after_fetch){
  let conn = null
  if( method.toUpperCase() == "POST" ){
    const data_source = document.querySelector(data_source_selector)
    conn = await fetch(url, {
      method: method,
      body: new FormData(data_source)
    })    
  }
  const data_from_server = await conn.text()
  if( ! conn){ console.log("error connecting to the server") }
  window[function_after_fetch](data_from_server)
}

function get_search_results(url, method, data_source_selector, function_after_fetch){
  const txt_search_for = document.querySelector("#txt_search_for")
  if( txt_search_for.value == ""  ){ 
    console.log("empty search"); 
    document.querySelector("#search_results").innerHTML = ""
    document.querySelector("#search_results").classList.add("d-none")
    return false 
  }
  server(url, method, data_source_selector, function_after_fetch)
}
function parse_search_results(data_from_server){
  // console.log(data_from_server)
  data_from_server = JSON.parse(data_from_server)
  let users = ""
  data_from_server.forEach( (user) => {
    let html = `
    <article id="user-${ user.user_pk }" md="flex-row p-items-center"
    class="d-flex j-content-between flex-col pt-.5rem">
    <div class="d-grid gap-2 cols-3 w-30% a-items-center">
        <div class="img-container w-3rem a-self-center">
            <img class="rounded-xs profile-icon"
                src="../static/${user.user_avatar_path}"
                alt="Profile">
        </div>
        <div class="d-flex flex-col ">
            <p class="ma-0 text-t-capitalize">
                ${user.user_first_name}
            </p>
            <p class="text-c-var(--color_tertiary)">
                ${user.user_email}
            </p>
        </div>
    </div>
    <div class="d-flex gap-2 p-self-end" md="p-self-center">
        <button class="button-secondary-small openDialogBtn" data-user="${ user.user_pk }">See reviews</button>

        ${
        user.user_deleted_at != 0
        ? `
            <button class="button-secondary-small"
                mix-patch="/reactivate-user?user_id=${user.user_pk}"
                mix-await="Reactivating user..."
                mix-default="Reactivate user">
                Reactivate user
            </button>
          `
        : `
            <button class="button-primary-small"
                mix-patch="/delete-user?user_id=${user.user_pk}"
                mix-await="Deleting user..."
                mix-default="Delete user">
                Delete user
            </button>
          `
        }
        
    </div>
    </article>
`
    users += html
  })
//   console.log(users)
  document.querySelector("#search_results").innerHTML = users
  document.querySelector("#search_results").classList.remove("d-none")
}

