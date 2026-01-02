"""
模糊测试 - 使用Hypothesis进行基于属性的测试
Property-Based Testing for Fuzzing
"""
from decimal import Decimal
from hypothesis import given, strategies as st, assume, settings
import pytest
from app.services.discount_engine import apply_discount, _quantize
from app.services.search import _normalize


class TestDiscountEngineFuzzing:
    """使用Hypothesis对折扣引擎进行模糊测试"""
    
    @given(
        base_price=st.decimals(min_value=0, max_value=999999, places=2),
        is_member=st.booleans(),
        min_price=st.decimals(min_value=0, max_value=999999, places=2),
        subsidy_cap=st.decimals(min_value=0, max_value=999999, places=2),
        coupon_discount=st.one_of(st.none(), st.decimals(min_value=0, max_value=999999, places=2))
    )
    @settings(max_examples=100)  # 生成100个随机测试用例
    def test_discount_never_negative(self, base_price, is_member, min_price, subsidy_cap, coupon_discount):
        """属性测试：最终价格永远不应该为负数"""
        final_price, platform_subsidy = apply_discount(
            base_price, is_member, min_price, subsidy_cap, coupon_discount
        )
        assert final_price >= Decimal("0"), f"Final price is negative: {final_price}"
        assert platform_subsidy >= Decimal("0"), f"Platform subsidy is negative: {platform_subsidy}"
    
    @given(
        base_price=st.decimals(min_value=0, max_value=999999, places=2),
        is_member=st.booleans(),
        min_price=st.decimals(min_value=0, max_value=999999, places=2),
        subsidy_cap=st.decimals(min_value=0, max_value=999999, places=2),
        coupon_discount=st.one_of(st.none(), st.decimals(min_value=0, max_value=999999, places=2))
    )
    @settings(max_examples=100)
    def test_final_price_not_exceeds_base_price_unless_min_price(self, base_price, is_member, min_price, subsidy_cap, coupon_discount):
        """属性测试：最终价格不应该超过原价（除非最低价格约束生效）"""
        final_price, _ = apply_discount(
            base_price, is_member, min_price, subsidy_cap, coupon_discount
        )
        # 如果最低价格大于原价，则最终价格会等于最低价格（这是预期行为）
        # 否则，最终价格应该小于等于原价
        if min_price > base_price:
            assert final_price == min_price, f"Final price should be min_price when min_price > base_price"
        else:
            assert final_price <= base_price, f"Final price {final_price} exceeds base price {base_price}"
    
    @given(
        base_price=st.decimals(min_value=0, max_value=999999, places=2),
        is_member=st.booleans(),
        min_price=st.decimals(min_value=0, max_value=999999, places=2),
        subsidy_cap=st.decimals(min_value=0, max_value=999999, places=2),
        coupon_discount=st.one_of(st.none(), st.decimals(min_value=0, max_value=999999, places=2))
    )
    @settings(max_examples=100)
    def test_min_price_always_respected(self, base_price, is_member, min_price, subsidy_cap, coupon_discount):
        """属性测试：最低价格保护始终生效"""
        final_price, _ = apply_discount(
            base_price, is_member, min_price, subsidy_cap, coupon_discount
        )
        assert final_price >= min_price, f"Final price {final_price} is below min price {min_price}"
    
    @given(
        base_price=st.decimals(min_value=0, max_value=999999, places=2),
        is_member=st.booleans(),
        min_price=st.decimals(min_value=0, max_value=999999, places=2),
        subsidy_cap=st.decimals(min_value=0, max_value=999999, places=2),
        coupon_discount=st.one_of(st.none(), st.decimals(min_value=0, max_value=999999, places=2))
    )
    @settings(max_examples=100)
    def test_subsidy_never_exceeds_cap(self, base_price, is_member, min_price, subsidy_cap, coupon_discount):
        """属性测试：平台补贴永远不超过上限"""
        _, platform_subsidy = apply_discount(
            base_price, is_member, min_price, subsidy_cap, coupon_discount
        )
        assert platform_subsidy <= subsidy_cap, f"Subsidy {platform_subsidy} exceeds cap {subsidy_cap}"
    
    @given(value=st.decimals(min_value=-999999, max_value=999999, places=5))
    @settings(max_examples=100)
    def test_quantize_always_returns_two_decimals(self, value):
        """属性测试：金额量化总是返回2位小数"""
        if value >= 0:
            result = _quantize(value)
            # 检查小数位数
            result_str = str(result)
            if '.' in result_str:
                decimal_places = len(result_str.split('.')[1])
                assert decimal_places <= 2, f"Quantize returned {decimal_places} decimal places"


class TestSearchServiceFuzzing:
    """使用Hypothesis对搜索服务进行模糊测试"""
    
    @given(text=st.text(min_size=0, max_size=1000))
    @settings(max_examples=100)
    def test_normalize_never_crashes(self, text):
        """属性测试：文本标准化函数不应该崩溃"""
        try:
            result = _normalize(text)
            # 标准化后的结果应该是字符串
            assert isinstance(result, str), f"Normalize returned non-string: {type(result)}"
            # 标准化后应该是小写
            assert result == result.lower(), f"Normalize didn't lowercase: {result}"
            # 标准化后不应该有前后空格
            assert result == result.strip(), f"Normalize didn't strip whitespace: '{result}'"
        except Exception as e:
            pytest.fail(f"Normalize crashed with input '{text[:50]}...': {e}")
    
    @given(text=st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll')), min_size=1, max_size=100))
    @settings(max_examples=100)
    def test_normalize_is_lowercase(self, text):
        """属性测试：标准化后应该全部是小写"""
        result = _normalize(text)
        # 标准化后应该全部是小写（某些Unicode字符可能例外）
        assert result == result.lower(), f"Normalized text is not all lowercase: '{result}'"
    
    @given(text=st.text(min_size=1, max_size=100))
    @settings(max_examples=100)
    def test_normalize_idempotent(self, text):
        """属性测试：标准化是幂等的（多次标准化结果相同）"""
        first = _normalize(text)
        second = _normalize(first)
        assert first == second, f"Normalize is not idempotent: '{first}' != '{second}'"


class TestEdgeCasesFuzzing:
    """测试边界情况的模糊测试"""
    
    @given(
        base_price=st.decimals(min_value=Decimal("0.01"), max_value=Decimal("0.09"), places=2),
        coupon=st.decimals(min_value=0, max_value=100, places=2)
    )
    @settings(max_examples=50)
    def test_small_price_large_coupon(self, base_price, coupon):
        """属性测试：小金额商品使用大额优惠券的情况"""
        min_price = Decimal("0.01")
        subsidy_cap = Decimal("50")
        
        final_price, subsidy = apply_discount(
            base_price, False, min_price, subsidy_cap, coupon
        )
        
        # 最终价格应该至少是最低价
        assert final_price >= min_price
        # 平台补贴不应超过上限
        assert subsidy <= subsidy_cap
    
    @given(
        base_price=st.decimals(min_value=999000, max_value=999999, places=2),
        is_member=st.booleans()
    )
    @settings(max_examples=50)
    def test_very_large_prices(self, base_price, is_member):
        """属性测试：处理非常大的价格时不应该溢出"""
        min_price = Decimal("100")
        subsidy_cap = Decimal("10000")
        
        final_price, subsidy = apply_discount(
            base_price, is_member, min_price, subsidy_cap, None
        )
        
        # 结果应该是有效的Decimal
        assert isinstance(final_price, Decimal)
        assert isinstance(subsidy, Decimal)
        # 不应该出现无穷大或NaN
        assert final_price.is_finite()
        assert subsidy.is_finite()
