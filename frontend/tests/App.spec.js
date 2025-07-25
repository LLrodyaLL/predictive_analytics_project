import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { createTestingPinia } from '@pinia/testing';
import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';
import App from '../src/App.vue';

const server = setupServer(
  http.post('http://localhost:8000/submit-request/', () => {
    return HttpResponse.json({
      article: '12345',
      region: 'МОСКВА - ЦФО',
      product_data: {
        revenue: 1000000,
        rating: 4.5,
        reviews_last_day: 50,
        brand_rating: 4.0,
        loyalty_level: 'Серебряный',
        has_promos: 1,
        promo_days: 10,
      },
    });
  }),
  http.get('http://localhost:8000/get-recommendation/', () => {
    return HttpResponse.json({ recommendation: 'Увеличить скидку на 5%' });
  })
);

describe('App.vue', () => {
  beforeEach(() => {
    server.listen();
  });

  afterEach(() => {
    server.resetHandlers();
    server.close();
  });

  it('рендерит заголовок и форму', () => {
    const wrapper = mount(App, {
      global: {
        plugins: [createTestingPinia()],
      },
    });

    expect(wrapper.find('.resname').exists()).toBe(true);
    expect(wrapper.find('.resname').text()).toBe('WB predictor');
    expect(wrapper.find('form.subForm').exists()).toBe(true);
    expect(wrapper.find('#articul').exists()).toBe(true);
    expect(wrapper.find('#region').exists()).toBe(true);
    expect(wrapper.find('#request').exists()).toBe(true);
    expect(wrapper.find('.form-submit').exists()).toBe(true);
  });

  it('кнопка отправки отключена, если форма не заполнена', async () => {
    const wrapper = mount(App, {
      global: {
        plugins: [createTestingPinia()],
      },
    });

    const submitButton = wrapper.find('.form-submit');
    expect(submitButton.attributes('disabled')).toBeDefined();

    await wrapper.find('#articul').find('input').setValue('12345');
    await wrapper.find('#region').find('.el-cascader').trigger('click');
    await wrapper.find('.el-cascader-menu__item').trigger('click');
    await wrapper.find('#request').find('input').setValue('футболка');

    await wrapper.vm.$nextTick();
    expect(submitButton.attributes('disabled')).toBeUndefined();
  });

  it('отправляет форму и обновляет таблицу productData', async () => {
    const wrapper = mount(App, {
      global: {
        plugins: [createTestingPinia()],
      },
    });

    await wrapper.find('#articul').find('input').setValue('12345');
    await wrapper.find('#region').find('.el-cascader').trigger('click');
    await wrapper.find('.el-cascader-menu__item').trigger('click');
    await wrapper.find('#request').find('input').setValue('футболка');
    await wrapper.find('form.subForm').trigger('submit');

    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick(); // Дополнительный тик для обработки асинхронности

    const tableRows = wrapper.findAll('.shpr tbody tr');
    expect(tableRows.length).toBeGreaterThan(0);
    expect(wrapper.text()).toContain('12345');
    expect(wrapper.text()).toContain('МОСКВА - ЦФО');
    expect(wrapper.text()).toContain('1000000');
    expect(wrapper.text()).toContain('4.5');
    expect(wrapper.text()).toContain('50');
    expect(wrapper.text()).toContain('4');
    expect(wrapper.text()).toContain('Серебряный');
    expect(wrapper.text()).toContain('Да');
    expect(wrapper.text()).toContain('10');
  });

  it('отображает сообщение об ошибке при неудачной отправке', async () => {
    server.use(
      http.post('http://localhost:8000/submit-request/', () => {
        return HttpResponse.json({ detail: 'Неверный артикул' }, { status: 400 });
      })
    );

    const wrapper = mount(App, {
      global: {
        plugins: [createTestingPinia()],
      },
    });

    await wrapper.find('#articul').find('input').setValue('12345');
    await wrapper.find('#region').find('.el-cascader').trigger('click');
    await wrapper.find('.el-cascader-menu__item').trigger('click');
    await wrapper.find('#request').find('input').setValue('футболка');
    await wrapper.find('form.subForm').trigger('submit');

    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();

    expect(wrapper.find('.error').exists()).toBe(true);
    expect(wrapper.find('.error').text()).toContain('Ошибка отправки: Неверный артикул');
  });

  it('получает рекомендации и обновляет таблицу recomendData', async () => {
    const wrapper = mount(App, {
      global: {
        plugins: [createTestingPinia()],
      },
    });

    await wrapper.find('button[type="success"]').trigger('click');
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();

    const recomendRows = wrapper.findAll('.rec tbody tr');
    expect(recomendRows.length).toBeGreaterThan(0);
    expect(wrapper.text()).toContain('Увеличить скидку на 5%');
  });

  it('открывает и закрывает диалоговое окно справки', async () => {
    const wrapper = mount(App, {
      global: {
        plugins: [createTestingPinia()],
      },
    });

    expect(wrapper.find('.el-dialog').exists()).toBe(false);

    await wrapper.find('.how').trigger('click');
    await wrapper.vm.$nextTick();
    expect(wrapper.find('.el-dialog').exists()).toBe(true);
    expect(wrapper.find('.el-dialog').text()).toContain('Здравствуйте! Я справка!');

    await wrapper.find('.dialog-footer .el-button').trigger('click');
    await wrapper.vm.$nextTick();
    expect(wrapper.find('.el-dialog').exists()).toBe(false);
  });

  it('отображает состояние загрузки на кнопке отправки', async () => {
    const wrapper = mount(App, {
      global: {
        plugins: [createTestingPinia()],
      },
    });

    await wrapper.find('#articul').find('input').setValue('12345');
    await wrapper.find('#region').find('.el-cascader').trigger('click');
    await wrapper.find('.el-cascader-menu__item').trigger('click');
    await wrapper.find('#request').find('input').setValue('футболка');
    await wrapper.find('form.subForm').trigger('submit');

    expect(wrapper.find('.form-submit').attributes('value')).toBe('Отправка...');
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    expect(wrapper.find('.form-submit').attributes('value')).toBe('Отправить');
  });
});