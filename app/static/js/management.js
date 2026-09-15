async function loadManagedCategories(){
  try{
    state.categories=await api("/api/categories");
    const select=$("#productCategory"),current=select.value;
    select.innerHTML=state.categories.map(c=>`<option value="${safe(c.name)}">${safe(c.name)}</option>`).join("");
    if(state.categories.some(c=>c.name===current))select.value=current;
    renderCategoryList();
  }catch(error){notice(error.message,true)}
}
function renderCategoryList(){
  const target=$("#categoryList");
  if(!target)return;
  target.innerHTML=state.categories.map(c=>`<div class="categoryRow"><input value="${safe(c.name)}" data-category-name="${c.id}" maxlength="100"><button class="secondary" data-category-save="${c.id}">Guardar</button><button class="danger" data-category-delete="${c.id}">Eliminar</button></div>`).join("")||'<div class="empty">No hay categorías</div>';
  $$('[data-category-save]').forEach(button=>button.onclick=()=>saveCategory(Number(button.dataset.categorySave)));
  $$('[data-category-delete]').forEach(button=>button.onclick=()=>deleteCategory(Number(button.dataset.categoryDelete)));
}
async function saveCategory(id){
  const name=$(`[data-category-name="${id}"]`).value;
  try{await api(`/api/categories/${id}`,{method:"PUT",body:JSON.stringify({name})});notice("Categoría actualizada");await Promise.all([loadManagedCategories(),loadProducts(),loadAdminProducts()])}catch(error){notice(error.message,true)}
}
async function deleteCategory(id){
  if(!confirm("¿Eliminar esta categoría?"))return;
  try{await api(`/api/categories/${id}`,{method:"DELETE"});notice("Categoría eliminada");await loadManagedCategories()}catch(error){notice(error.message,true)}
}
$("#manageCategories").onclick=async()=>{await loadManagedCategories();$("#categoryModal").showModal()};
$("#categoryForm").onsubmit=async event=>{
  event.preventDefault();const name=event.target.elements.name.value;
  try{await api("/api/categories",{method:"POST",body:JSON.stringify({name})});event.target.reset();notice("Categoría creada");await loadManagedCategories()}catch(error){notice(error.message,true)}
};

async function loadProductReport(){
  try{
    const from=$("#reportFrom").value,to=$("#reportTo").value,params=new URLSearchParams();
    if(from)params.set("date_from",from);if(to)params.set("date_to",to);
    const report=await api(`/api/reports/products-sold?${params}`);
    $("#reportMetrics").innerHTML=`<div class="metric"><span>Unidades vendidas</span><strong>${report.total_units}</strong></div><div class="metric"><span>Productos diferentes</span><strong>${report.distinct_products}</strong></div><div class="metric"><span>Importe vendido</span><strong>${money(report.total_revenue)}</strong></div>`;
    $("#productReportTable").innerHTML=report.products.map(p=>`<tr><td><strong>${safe(p.product_name)}</strong></td><td>${p.quantity}</td><td>${p.sales_count}</td><td><strong>${money(p.revenue)}</strong></td></tr>`).join("")||'<tr><td colspan="4">No hay productos vendidos en este periodo</td></tr>';
  }catch(error){notice(error.message,true)}
}
$("#loadReport").onclick=loadProductReport;
$('[data-view="sales"]').addEventListener("click",loadProductReport);
loadManagedCategories();
