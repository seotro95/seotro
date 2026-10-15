def supports_int8():
    try:
        from numpy._core._multiarray_umath import __cpu_features__
        return bool(__cpu_features__.get('AVX512VNNI') or __cpu_features__.get('AVXVNNI'))
    except (ImportError, AttributeError):
        return False
