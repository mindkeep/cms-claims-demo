def test_package_importable() -> None:
    import cms_platform

    assert cms_platform.__version__ == "0.1.0"
