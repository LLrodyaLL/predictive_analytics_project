<template>
  <div class="bod">
    <div class="up">
      <h1 class="resname">WB predictor</h1>
      <el-button class="how" size="large" type="info" @click="infoWindow = true" circle>?</el-button>
    </div>

    <div class="search">
      <h4>Введите артикул, регион и запрос</h4>
      <form @submit.prevent="submitForm" class="subForm">
        <div class="form-group">
          <label for="articul">Артикул</label><br />
          <el-input id="articul" data-testid="articul-input" v-model="formData.article" required />
        </div>
        <div class="form-group">
          <label for="region">Регион</label><br />
          <el-cascader id="region" data-testid="region-input" v-model="formData.region" :options="regions" :disabled="isLoading" required />
        </div>
        <div class="form-group">
          <label for="request">Запрос</label><br />
          <el-input id="request" data-testid="request-input" v-model="formData.query" required />
        </div>
        <input
          type="submit"
          class="form-submit"
          :disabled="!isFormValid || isLoading"
          :value="isLoading ? 'Отправка...' : 'Отправить'"
        />
      </form>
      <p v-if="error" class="error">{{ error }}</p>
      <p v-if="successMessage" class="success">{{ successMessage }}</p>
    </div>

    <div class="show-product">
      <el-table :data="productData" class="shpr">
        <el-table-column prop="article" label="Артикул" />
        <el-table-column prop="region" label="Гео" />
        <el-table-column prop="revenue" label="Выручка" />
        <el-table-column prop="rating" label="Рейтинг товара" />
        <el-table-column prop="reviews_last_day" label="Кол-во отзывов на конец периода" />
        <el-table-column prop="brand_rating" label="Рейтиннг продавца" />
        <el-table-column prop="loyalty_level" label="Уровень в программе лояльности" />
        <el-table-column prop="has_promos" label="Участие в акциях" />
        <el-table-column prop="promo_days" label="Продолжительность участия" />
      </el-table>
    </div>

    <div class="recomend">
      <el-button type="success" @click="getRecomendations" :disabled="isLoadingRec" data-testid="get-recommend-btn">Получить рекомендации</el-button>
    </div>

    <div class="recomend_list">
      <el-table :data="recomendData" class="rec">
        <el-table-column prop="recomendation" label="Рекомендации" header-align="center" align="center" />
      </el-table>
    </div>
  </div>

  <el-dialog v-model="infoWindow" title="Справка" width="500" align-center>
    <span>
      Здравствуйте! Я справка!<br />
      1. Укажите артикул товара, регион и введите запрос.<br />
      2. Получите данные по товару.<br />
      3. Вы можете посмотреть рекомендацию по продвижению, нажав соответствующую кнопку.<br />
      4. Для сброса данных перезагрузите страницу.
    </span>
    <template #footer>
      <div class="dialog-footer">
        <el-button type="primary" @click="infoWindow = false">Confirm</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed } from 'vue';
import axios from 'axios';

const regions = ref([
  { value: 'МОСКВА - ЦФО', label: 'МОСКВА - ЦФО' },
  { value: 'САНКТ-ПЕТЕРБУРГ - СЗФО', label: 'САНКТ-ПЕТЕРБУРГ - СЗФО' },
  { value: 'КРАСНОДАР - ЮФО', label: 'КРАСНОДАР - ЮФО' },
  { value: 'КАЗАНЬ - ПФО', label: 'КАЗАНЬ - ПФО' },
  { value: 'ЕКАТЕРИНБУРГ - УФО', label: 'ЕКАТЕРИНБУРГ - УФО' },
  { value: 'НОВОСИБИРСК - СФО', label: 'НОВОСИБИРСК - СФО' },
  { value: 'ХАБАРОВСК - ДФО', label: 'ХАБАРОВСК - ДФО' }
]);

const formData = ref({ article: '', region: '', query: '' });
const productData = ref([]);
const recomendData = ref([]);
const isLoading = ref(false);
const isLoadingRec = ref(false);
const error = ref('');
const successMessage = ref('');
const infoWindow = ref(false);

const isFormValid = computed(() => {
  return formData.value.article && formData.value.region && formData.value.query;
});

const submitForm = async () => {
  if (!isFormValid.value) return;

  isLoading.value = true;
  error.value = '';
  successMessage.value = '';
  formData.value.region = formData.value.region[0];

  try {
    const response = await axios.post('http://localhost:8000/submit-request/', formData.value, {
      headers: { 'Content-Type': 'application/json' }
    });

    formData.value = { article: '', region: '', query: '' };
    productData.value.push({
      article: response.data.article,
      region: response.data.region,
      revenue: response.data.product_data.revenue,
      rating: response.data.product_data.rating,
      reviews_last_day: response.data.product_data.reviews_last_day,
      brand_rating: response.data.product_data.brand_rating,
      loyalty_level: response.data.product_data.loyalty_level,
      has_promos: response.data.product_data.has_promos === 1 ? 'Да' : 'Нет',
      promo_days: response.data.product_data.promo_days
    });
  } catch (err) {
    error.value = `Ошибка отправки: ${err.response?.data?.detail || err.response?.data?.message || err.message}`;
  } finally {
    isLoading.value = false;
  }
};

const getRecomendations = async () => {
  try {
    isLoadingRec.value = true;
    const response = await axios.get('http://localhost:8000/get-recommendation/');
    recomendData.value = [{ recomendation: response.data.recommendation }];
  } catch (error) {
    console.error('Ошибка при получении рекомендаций:', error);
  } finally {
    isLoadingRec.value = false;
  }
};
</script>

<style scoped>
.bod {
  background: purple;
  display: flex;
  flex-direction: column;
  gap: 50px;
}
.up {
  display: flex;
  justify-content: center;
  align-items: center;
  position: relative;
  height: 6vh;
  width: 100%;
}
.how {
  position: absolute;
  right: 20px;
}
.resname {
  color: red;
  margin: 0;
}
.subForm {
  display: flex;
  gap: 20px;
  align-items: flex-end;
}
.form-group {
  display: flex;
  flex-direction: column;
}
.form-group label {
  margin-bottom: 5px;
}
.form-group input {
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
}
.form-submit {
  align-self: center;
}
.recomend {
  margin-left: 20px;
}
.recomend_list {
  margin: 0 20px 5px 20px;
  border-radius: 8px;
}
.rec {
  border-radius: 8px;
}
.search {
  border-radius: 8px;
  padding: 20px;
  background: white;
  width: fit-content;
  margin-left: 20px;
}
.show-product {
  margin: 0 20px;
  border-radius: 8px;
}
.shpr {
  max-height: 300px;
  width: 100%;
  border-radius: 8px;
}
html,
body {
  margin: 0;
  padding: 0;
  height: 100%;
}
</style>
