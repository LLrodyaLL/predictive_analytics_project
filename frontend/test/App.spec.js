import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import App from '../src/App.vue'
import axios from 'axios'

vi.mock('axios')

describe('App.vue', () => {
  let wrapper

  beforeEach(() => {
    wrapper = mount(App, {
      attachTo: document.body, // для работы с DOM
      global: {
        stubs: {
          'el-input': {
            template: `<input v-bind="$attrs" @input="$emit('update:modelValue', $event.target.value)" />`
          },
          'el-cascader': {
            template: `<select v-bind="$attrs" @change="$emit('update:modelValue', [$event.target.value])">
              <option value="МОСКВА - ЦФО">МОСКВА - ЦФО</option>
            </select>`
          },
          'el-button': {
            template: `<button v-bind="$attrs" @click="$emit('click')"><slot /></button>`
          },
          'el-table': true,
          'el-table-column': true,
          'el-dialog': true
        }
      }
    })
  })

  it('отображает заголовок', () => {
    expect(wrapper.text()).toContain('WB predictor')
  })

  it('отображает форму с полями: артикул, регион и запрос', () => {
    expect(wrapper.find('[data-testid="articul-input"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="region-input"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="request-input"]').exists()).toBe(true)
  })

  it('отображает кнопку отправки', () => {
    const button = wrapper.find('input[type="submit"]')
    expect(button.exists()).toBe(true)
  })

  it('успешно отправляет форму и отображает таблицу', async () => {
    axios.post.mockResolvedValue({
      data: {
        article: '123456',
        region: 'МОСКВА - ЦФО',
        product_data: {
          revenue: 10000,
          rating: 4.5,
          reviews_last_day: 20,
          brand_rating: 4.8,
          loyalty_level: 'Золотой',
          has_promos: 1,
          promo_days: 7
        }
      }
    })

    await wrapper.find('[data-testid="articul-input"]').setValue('123456')
    await wrapper.find('[data-testid="region-input"]').setValue('МОСКВА - ЦФО')
    await wrapper.find('[data-testid="request-input"]').setValue('запрос')
    await wrapper.find('form').trigger('submit.prevent')

    // Проверка результата
    expect(wrapper.vm.productData.length).toBe(1)
    expect(wrapper.vm.productData[0].article).toBe('123456')
  })

  it('запрашивает рекомендации и отображает их', async () => {
    axios.get.mockResolvedValue({
      data: { recommendation: 'Снизьте цену на 10%' }
    })

    const btn = wrapper.find('[data-testid="get-recommend-btn"]')
    expect(btn.exists()).toBe(true)
    await btn.trigger('click')

    expect(wrapper.vm.recomendData[0].recomendation).toBe('Снизьте цену на 10%')
  })
})
